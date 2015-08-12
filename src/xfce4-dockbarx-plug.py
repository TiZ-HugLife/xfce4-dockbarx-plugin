#!/usr/bin/python2
#
#   xfce4-dockbarx-plug
#
#   Copyright 2008-2013
#      Aleksey Shaferov, Matias Sars, and Trent McPheron
#
#   DockbarX is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   DockbarX is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with dockbar.  If not, see <http://www.gnu.org/licenses/>.

from dockbarx.log import *
import sys
import io
import os
import subprocess
import time
log_to_file()
sys.stderr = StdErrWrapper()
sys.stdout = StdOutWrapper()
import traceback

# Wait for just one second, make sure config files and the like get settled.
time.sleep(1)

import pygtk
pygtk.require("2.0")
import gtk
import cairo
import gobject
import dbus

import dockbarx.dockbar as db
from dockbarx.common import Globals
from ConfigParser import SafeConfigParser


# Create a cairo pattern from given color.
def make_color_pattern (size, red, green, blue, alpha):
    if gtk.gdk.screen_get_default().get_rgba_colormap() is None: alpha = 100
    return cairo.SolidPattern(red / size, green / size, blue / size,
     alpha / 100.0)

# Create a cairo pattern from given image.
def make_image_pattern (image, offset, orient):
    try:
        surface = cairo.ImageSurface.create_from_png(image)
        pattern = cairo.SurfacePattern(surface)
        pattern.set_extend(cairo.EXTEND_REPEAT)
    except:
        traceback.print_exc()
        sys.exit("Couldn't load png image.")
    try:
        tx = offset if orient in ("up", "down") else 0
        ty = offset if orient in ("left", "right") else 0
        matrix = cairo.Matrix(x0=tx, xy=ty)
        pattern.set_matrix(matrix)
    except:
        traceback.print_exc()
        sys.exit("Image offset must be an integer.")
    return pattern

# Create a pattern from dbus.
def pattern_from_dbus (iface, prop, offset, orient):
    style = iface.GetProperty("xfce4-panel", prop + "background-style")
    if style == 2:
        image = iface.GetProperty("xfce4-panel", prop + "background-image")
        return make_image_pattern(image, offset, orient)
    else:
        color = iface.GetProperty("xfce4-panel", prop + "background-color")
        alpha = iface.GetProperty("xfce4-panel", prop + "background-alpha")
        return make_color_pattern(65535.0, color[0], color[1], color[2], alpha)

# A very minimal plug application that loads DockbarX
# so that the embed plugin can, well, embed it.
class DockBarXFCEPlug(gtk.Plug):
    # We want to do our own expose instead of the default.
    __gsignals__ = {"expose-event": "override"}

    # Constructor!
    def __init__ (self, socket, cairo_pattern, offset, orient, max_size, expand,
     bus=None, iface=None, xfconf_prop=None):
        # Set up the window.
        gtk.Plug.__init__(self, socket)
        self.pattern = cairo_pattern
        self.max_size = max_size
        self.expand = expand
        self.offset = offset
        self.orient = orient
        self.set_name("Xfce4DockBarXPlug")
        self.connect("destroy", self.destroy)
        self.set_app_paintable(True)
        gtk_screen = gtk.gdk.screen_get_default()
        colormap = gtk_screen.get_rgba_colormap()
        if colormap is None: colormap = gtk_screen.get_rgb_colormap()
        self.set_colormap(colormap)

        # Load and insert DBX.
        self.dockbar = db.DockBar(self)
        self.dockbar.set_orient(orient)
        self.dockbar.set_expose_on_clear(True)
        self.dockbar.load()
        self.add(self.dockbar.get_container())
        self.dockbar.set_max_size(self.max_size)
        self.show_all()
        
        # Set up dbus integration.
        if bus:
            self.bus = bus
            self.iface = iface
            self.prop = prop
            bus.add_signal_receiver(self.xfconf_changed, "PropertyChanged",
             "org.xfce.Xfconf", "org.xfce.Xfconf", "/org/xfce/Xfconf")
    
    def xfconf_changed (self, channel, prop, val):
        if channel != "xfce4-panel": return
        if self.prop not in prop: return
        self.pattern = pattern_from_dbus(self.iface, self.prop, self.offset,
         self.orient)
        self.queue_draw()
    
    def readd_container (self, container):
        # Dockbar calls back with this function when it is reloaded
        # since the old container has been destroyed in the reload
        # and needs to be added again.
        self.add(container)
        self.dockbar.set_max_size(self.max_size)
        container.show_all()

    # This is basically going to do what xfce4-panel
    # does on its own expose events.
    def do_expose_event (self, event):
        self.window.set_back_pixmap(None, False)
        ctx = self.window.cairo_create()
        ctx.set_antialias(cairo.ANTIALIAS_NONE)
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.rectangle(event.area.x, event.area.y,
                      event.area.width, event.area.height)
        ctx.clip()
        ctx.set_source(self.pattern)
        ctx.paint()
        if self.get_child():
            self.propagate_expose(self.get_child(), event)

    # Destructor?
    def destroy (self, widget, data=None):
        gtk.main_quit()

# Init the variables to default values.
socket = 0
config = ""
bus = None
xfconf = None
prop = None

# Then check the arguments for them.
if "-s" in sys.argv:
    i = sys.argv.index("-s") + 1
    try:
        socket = int(sys.argv[i])
    except:
        raise
if "-c" in sys.argv:
    i = sys.argv.index("-c") + 1
    try:
        config = sys.argv[i]
    except:
        raise

# If you try to run this by itself, you're bad and you should feel bad.
if socket == 0:
    sys.exit("Stop it. This program needs to be run by the XFCE embed plugin.")

# You also need a configuration file, you bad program user.
if config == "":
    sys.exit("Forgetting something? You need a configuration file.")

# First, load the configuration file.
# Default config.
default_conf = """
[Xfce4DockbarX]
config=false
mode=0
color=#3c3c3c
alpha=100
image=
offset=0
max_size=0
orient=bottom
expand=false
"""

# Scope crap.
mode = 0
color = "#3c3c3c"
alpha = 100
image = ""
offset = 0
max_size = 0
expand = False
orient = "bottom"
cairo_pattern = None
section = "Xfce4DockbarX"

keyfile = SafeConfigParser(allow_no_value=True)
try:
    keyfile.readfp(io.BytesIO(default_conf))
    keyfile.read(config)

    # Read the config.
    mode = keyfile.getint(section, "mode")
    orient = keyfile.get(section, "orient")
except:
    traceback.print_exc()
    sys.exit("Couldn't load config.")

# Let's make sure our parameters are actually valid.
if not (orient == "bottom" or orient == "top" or
 orient == "left" or orient == "right"):
    sys.exit("Orient must be bottom, top, left, or right.")

# Change it to DBX-specific terminology.
if orient == "bottom": orient = "down"
if orient == "top": orient = "up"

# Color parameters.
if mode == 0:
    try:
        alpha = keyfile.getint(section, "alpha")
    except:
        sys.exit("Alpha must be between 0 for transparent and 100 for opaque.")
    try:
        # Ungraceful, but easy. Sue me.
        c = keyfile.get(section, "color")
        if c[0] == "#": c = c[1:]
        split = ""
        size = 0.0
        if len(c) == 3:
            split = (c[0:1], c[1:2], c[2:3])
            size = 15.0
        if len(c) == 6:
            split = (c[0:2], c[2:4], c[4:6])
            size = 255.0
        if len(c) == 9:
            split = (c[0:3], c[3:6], c[6:9])
            size = 4095.0
        if len(c) == 12:
            split = (c[0:4], c[4:8], c[8:12])
            size = 65535.0
        cl = [int(x, 16) for x in split]
        cairo_pattern = make_color_pattern(size, cl[0], cl[1], cl[2], alpha);
    except:
        traceback.print_exc()
        sys.exit("Color must be specified in hex: red, green, blue.")

# Image parameters.
elif mode == 1:
    cairo_pattern = make_image_pattern(keyfile.get(section, "image"),
     keyfile.getint(section, "offset"), orient)

# Fancy new panel blend mode which uses DBus!
elif mode == 2:
    bus = dbus.SessionBus()
    xfconf = dbus.Interface(bus.get_object(
     "org.xfce.Xfconf", "/org/xfce/Xfconf"), "org.xfce.Xfconf")
    prop = "/panels/panel-{}/".format(keyfile.getint(section, "blend_panel"));
    cairo_pattern = pattern_from_dbus(xfconf, prop, offset, orient)

else:
    sys.exit("Mode must be 0 for color, 1 for image, or 2 for blend.")

# Size parameters.
try:
    max_size = keyfile.getint(section, "max_size")
    if max_size == 0: max_size = 4096
except:
    traceback.print_exc()
    sys.exit("Max_size must be a positive integer.")
try:
    expand = keyfile.getboolean(section, "expand")
except:
    traceback.print_exc()
    sys.exit("Expand must be true or false.")

# Anyways, time to start DBX!
dockbarxplug = DockBarXFCEPlug(socket, cairo_pattern, offset, orient, max_size,
 expand, bus, xfconf, prop)
gtk.main()
