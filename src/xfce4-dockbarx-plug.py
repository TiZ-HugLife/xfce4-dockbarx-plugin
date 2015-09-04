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
        self.dbx_prop = None
        self.panel_prop = None
        section = "Xfce4DockbarX"

        # Then check the arguments for them.
        parser = OptionParser()
        parser.add_option("-s", "--socket", default = 0, help = "Socket ID")
        parser.add_option("-i", "--plugin_id", default = -1, help = "Plugin ID")
        (options, args) = parser.parse_args()

        # Sanity checks.
        if options.socket == 0:
            sys.exit("This program needs to be run by the XFCE DBX plugin.")
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

        # Set up DBus.
        self.bus = dbus.SessionBus()
        self.xfconf = dbus.Interface(self.bus.get_object(
         "org.xfce.Xfconf", "/org/xfce/Xfconf"), "org.xfce.Xfconf")
        self.dbx_prop = "/plugins/plugin-" + options.plugin_id + "/"
        self.panel_prop = [k for (k, v) in
         self.xfconf.GetAllProperties("xfce4-panel", "/panels").iteritems()
         if "plugin-ids" in k and int(options.plugin_id) in v][0][:-10]

        self.mode = self.xfconf_get_dbx("mode", 2)
        self.orient = self.xfconf_get_dbx("orient", "down")
        self.offset = self.xfconf_get_dbx("offset", 0)

        # Let's make sure our parameters are actually valid.
        if not (self.orient == "bottom" or self.orient == "top" or
         self.orient == "down" or self.orient == "up" or
         self.orient == "left" or self.orient == "right"):
            sys.exit("Orient must be bottom, top, left, or right.")

        # Change it to DBX-specific terminology.
        if self.orient == "bottom": self.orient = "down"
        if self.orient == "top": self.orient = "up"

        # Prepare panel background.
        image = self.xfconf_get_dbx("image", "")
        if self.mode == 1 and os.path.isfile(image):
            self.image_pattern(image)
        elif self.mode == 0:
            alpha = self.xfconf_get_dbx("alpha", 100)
            color = gtk.gdk.color_parse(self.xfconf_get_dbx("color", "#000"))
            self.color_pattern(color, alpha);
        else:
            self.pattern_from_dbus()
            self.bus.add_signal_receiver(self.xfconf_changed, "PropertyChanged",
             "org.xfce.Xfconf", "org.xfce.Xfconf", "/org/xfce/Xfconf")

        # Size parameters.
        self.max_size = self.xfconf_get_dbx("max_size", 0)
        if self.max_size < 1: self.max_size = 4096
        self.expand = self.xfconf_get_dbx("expand", False)
        
        # Load and insert DBX.
        self.dockbar = db.DockBar(self)
        self.dockbar.set_orient(self.orient)
        self.dockbar.set_expose_on_clear(True)
        self.dockbar.load()
        self.add(self.dockbar.get_container())
        self.dockbar.set_max_size(self.max_size)
        self.show_all()
    
    # Convenience methods.
    def xfconf_get (self, prop_base, prop, default=None):
        if self.xfconf.PropertyExists("xfce4-panel", prop_base + prop):
            retval = self.xfconf.GetProperty("xfce4-panel", prop_base + prop)
            if type(retval) is type(default) or default is None:
                return retval
            else:
                return default
        else:
            return default
    def xfconf_get_dbx (self, prop, default=None):
        return self.xfconf_get(self.dbx_prop, prop, default)
    def xfconf_get_panel (self, prop, default=None):
        return self.xfconf_get(self.panel_prop, prop, default)
    
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
    
    # Create a pattern from dbus.
    def pattern_from_dbus (self):
        style = self.xfconf_get_panel("background-style", 0)
        image = self.xfconf_get_panel("background-image", "")
        if style == 2 and os.path.isfile(image):
            image = self.xfconf_get_panel("background-image", "")
            self.image_pattern(image)
        elif style == 1:
            col = self.xfconf_get_panel("background-color", [0, 0, 0, 0])
            alpha = self.xfconf_get_panel("background-alpha", 100)
            self.color_pattern(gtk.gdk.Color(col[0], col[1], col[2]), alpha)
        else:
            style = self.get_style()
            alpha = self.xfconf_get_panel("background-alpha")
            self.color_pattern(style.bg[gtk.STATE_NORMAL], alpha)
    
    def xfconf_changed (self, channel, prop, val):
        if channel != "xfce4-panel": return
        if self.panel_prop not in prop: return
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
