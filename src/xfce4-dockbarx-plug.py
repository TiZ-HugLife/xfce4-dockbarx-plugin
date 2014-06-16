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

import dockbarx.dockbar as db
from dockbarx.common import Globals
from ConfigParser import SafeConfigParser


# A very minimal plug application that loads DockbarX
# so that the embed plugin can, well, embed it.
class DockBarXFCEPlug(gtk.Plug):
    # We want to do our own expose instead of the default.
    __gsignals__ = {"expose-event": "override"}

    # Constructor!
    def __init__ (self, socket, cairo_pattern, orient):
        # Set up the window.
        gtk.Plug.__init__(self, socket)
        self.pattern = cairo_pattern
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
        self.show_all()

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
mode=0
color=#3c3c3c
alpha=100
image=null
offset=0
orient=bottom
"""

# Scope crap.
mode = 0
color = "#3c3c3c"
alpha = 100
image = ""
offset = 0
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
        cl = [(int(x, 16) / 65535.0) for x in split]
        if gtk.gdk.screen_get_default().get_rgba_colormap() is None: alpha = 100
        cairo_pattern = cairo.SolidPattern(cl[0], cl[1], cl[2], alpha / 100.0)
    except:
        traceback.print_exc()
        sys.exit("Color must be specified in hex: red, green, blue.")

# Image parameters.
elif mode == 1:
    try:
        image = keyfile.get(section, "image")
        surface = cairo.ImageSurface.create_from_png(image)
        cairo_pattern = cairo.SurfacePattern(surface)
        cairo_pattern.set_extend(cairo.EXTEND_REPEAT)
    except:
        traceback.print_exc()
        sys.exit("Couldn't load png image.")
    try:
        offset = keyfile.getint(section, "offset")
        tx = offset if orient in ("up", "down") else 0
        ty = offset if orient in ("left", "right") else 0
        matrix = cairo.Matrix(x0=tx, xy=ty)
        cairo_pattern.set_matrix(matrix)
    except:
        traceback.print_exc()
        sys.exit("Image offset must be an integer.")
else:
    sys.exit("Mode must be 0 for color or 1 for image.")

# Anyways, time to start DBX!
dockbarxplug = DockBarXFCEPlug(socket, cairo_pattern, orient)
gtk.main()
