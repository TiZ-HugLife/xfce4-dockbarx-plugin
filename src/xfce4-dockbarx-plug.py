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

from dockbarx.log import *; log_to_file()
import sys
sys.stderr = StdErrWrapper()
sys.stdout = StdOutWrapper()
import io
import traceback

import pygtk
pygtk.require("2.0")
import gtk
import cairo
import dbus

import dockbarx.dockbar as db
from ConfigParser import SafeConfigParser
from optparse import OptionParser


# A very minimal plug application that loads DockbarX
# so that the embed plugin can, well, embed it.
class DockBarXFCEPlug(gtk.Plug):
    # We want to do our own expose instead of the default.
    __gsignals__ = {"expose-event": "override"}

    # Constructor!
    def __init__ (self):
        # Init the variables to default values.
        self.bus = None
        self.xfconf = None
        self.prop = None
        section = "Xfce4DockbarX"

        # Then check the arguments for them.
        parser = OptionParser()
        parser.add_option("-s", "--socket", default = 0, help = "Socket ID")
        parser.add_option("-c", "--config", default = "", help = "Config file")
        parser.add_option("-i", "--plugin_id", default = -1, help = "Plugin ID")
        (options, args) = parser.parse_args()

        # Sanity checks.
        if options.socket == 0:
            sys.exit("This program needs to be run by the XFCE DBX plugin.")
        if options.config == "":
            sys.exit("Forgetting something? You need a configuration file.")
        if options.plugin_id == -1:
            sys.exit("We need to know the plugin id of the DBX socket.")
        
        # Set up the window.
        gtk.Plug.__init__(self, int(options.socket))
        self.connect("destroy", self.destroy)
        self.get_settings().connect("notify::gtk-theme-name",self.theme_changed)
        self.set_app_paintable(True)
        gtk_screen = gtk.gdk.screen_get_default()
        colormap = gtk_screen.get_rgba_colormap()
        if colormap is None: colormap = gtk_screen.get_rgb_colormap()
        self.set_colormap(colormap)
        
        # This should cause the widget to get themed like a panel.
        self.set_name("Xfce4PanelDockBarX")
        self.show()

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

        keyfile = SafeConfigParser(allow_no_value=True)
        try:
            keyfile.readfp(io.BytesIO(default_conf))
            keyfile.read(options.config)

            # Read the config.
            self.mode = keyfile.getint(section, "mode")
            self.orient = keyfile.get(section, "orient")
            self.offset = keyfile.getint(section, "offset")
        except:
            traceback.print_exc()
            sys.exit("Couldn't load config.")

        # Let's make sure our parameters are actually valid.
        if not (self.orient == "bottom" or self.orient == "top" or
         self.orient == "down" or self.orient == "up" or
         self.orient == "left" or self.orient == "right"):
            sys.exit("Orient must be bottom, top, left, or right.")

        # Change it to DBX-specific terminology.
        if self.orient == "bottom": self.orient = "down"
        if self.orient == "top": self.orient = "up"

        # Color parameters.
        if self.mode == 0:
            try:
                alpha = keyfile.getint(section, "alpha")
            except:
                sys.exit("Alpha must be 0 for transparent to 100 for opaque.")
            try:
                color = gtk.gdk.color_parse(keyfile.get(section, "color"))
                self.color_pattern(color, alpha);
            except:
                traceback.print_exc()
                sys.exit("Color must be specified in hex: #rrggbb.")

        # Image parameters.
        elif self.mode == 1:
            self.image_pattern(keyfile.get(section, "image"))

        # Fancy new panel blend mode which uses DBus!
        elif self.mode == 2:
            self.bus = dbus.SessionBus()
            self.xfconf = dbus.Interface(self.bus.get_object(
             "org.xfce.Xfconf", "/org/xfce/Xfconf"), "org.xfce.Xfconf")
            self.prop = [k for (k, v) in
             self.xfconf.GetAllProperties("xfce4-panel", "/panels").iteritems()
             if "plugin-ids" in k and int(options.plugin_id) in v][0][:-10]
            self.pattern_from_dbus()
            self.bus.add_signal_receiver(self.xfconf_changed, "PropertyChanged",
             "org.xfce.Xfconf", "org.xfce.Xfconf", "/org/xfce/Xfconf")

        else:
            sys.exit("Mode must be 0 for color, 1 for image, or 2 for blend.")

        # Size parameters.
        try:
            self.max_size = keyfile.getint(section, "max_size")
            if self.max_size == 0: self.max_size = 4096
        except:
            traceback.print_exc()
            sys.exit("Max_size must be a positive integer.")
        try:
            self.expand = keyfile.getboolean(section, "expand")
        except:
            traceback.print_exc()
            sys.exit("Expand must be true or false.")
        
        # Load and insert DBX.
        self.dockbar = db.DockBar(self)
        self.dockbar.set_orient(self.orient)
        self.dockbar.set_expose_on_clear(True)
        self.dockbar.load()
        self.add(self.dockbar.get_container())
        self.dockbar.set_max_size(self.max_size)
        self.show_all()
    
    # Create a cairo pattern from given color.
    def color_pattern (self, color, alpha):
        if gtk.gdk.screen_get_default().get_rgba_colormap() is None: alpha = 100
        self.pattern = cairo.SolidPattern(color.red_float, color.green_float,
         color.blue_float, alpha / 100.0)

    # Create a cairo pattern from given image.
    def image_pattern (self, image):
        try:
            surface = cairo.ImageSurface.create_from_png(image)
            self.pattern = cairo.SurfacePattern(surface)
            self.pattern.set_extend(cairo.EXTEND_REPEAT)
        except:
            traceback.print_exc()
            sys.exit("Couldn't load png image.")
        try:
            tx = self.offset if self.orient in ("up", "down") else 0
            ty = self.offset if self.orient in ("left", "right") else 0
            matrix = cairo.Matrix(x0=tx, xy=ty)
            self.pattern.set_matrix(matrix)
        except:
            traceback.print_exc()
            sys.exit("Image offset must be an integer.")
    
    # Convenience method.
    def get_xfconf_panel (self, prop):
        return self.xfconf.GetProperty("xfce4-panel", self.prop + prop)
    
    # Create a pattern from dbus.
    def pattern_from_dbus (self):
        style = self.get_xfconf_panel("background-style")
        if style == 2:
            image = self.get_xfconf_panel("background-image")
            self.image_pattern(image)
        elif style == 1:
            col = self.get_xfconf_panel("background-color")
            alpha = self.get_xfconf_panel("background-alpha")
            self.color_pattern(gtk.gdk.Color(col[0], col[1], col[2]), alpha)
        else:
            style = self.get_style()
            alpha = self.get_xfconf_panel("background-alpha")
            self.color_pattern(style.bg[gtk.STATE_NORMAL], alpha)
    
    def xfconf_changed (self, channel, prop, val):
        if channel != "xfce4-panel": return
        if self.prop not in prop: return
        self.pattern_from_dbus()
        self.queue_draw()
    
    def theme_changed (self, obj, prop):
        self.pattern_from_dbus()
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

# Start DBX.
if __name__ == '__main__':
    # Wait for just one second, make sure config files and the like get settled.
    import time; time.sleep(1)
    dbx = DockBarXFCEPlug()
    gtk.main()
