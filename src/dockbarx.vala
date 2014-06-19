// Copyright (c) 2013- Trent McPheron <twilightinzero@gmail.com>
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.

using Xfce;
using Gtk;


// xfce4-panel uses this to register the plugin.
[ModuleInit]
public Type xfce_panel_module_init (TypeModule module) {
    return typeof (DockbarXPlugin);
}

// The actual DockbarX plugin class.
public class DockbarXPlugin : PanelPlugin {

    // Fields and props.
    private Gtk.Socket   socket;
    private ulong        socket_id;
    private bool         starting_dbx = false;
    public  uint8        bgmode      { get; set; }
    public  Gdk.Color    color;  // Can't be a property.
    public  uint8        alpha       { get; set; }
    public  string       image       { get; set; }
    public  int          offset      { get; set; }
    public  int          max_size    { get; set; }
    public  bool         config      { get; set; }
    public  string       orient      { get; set; }
    public  bool         free_orient { get; set; default = false; }
    private const string section = "Xfce4DockbarX";

    // Constructor!
    public override void @construct () {
        // This program does one thing, and one thing only:
        // Embeds the already-made DockBarX using the helper
        // application, dockbarx-xfce-plug.

        // Load settings from the rc file.
        KeyFile keyfile = new KeyFile();
        try {
            // Load the default config.
            keyfile.load_from_data("""
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
            """, -1, KeyFileFlags.NONE);
            // Load the keyfile.
        } catch {
            stderr.printf("The default config got messed up somehow...");
        }
        try {
            keyfile.load_from_file(lookup_rc_file(), KeyFileFlags.NONE);
        } catch { }
        try {
            config = keyfile.get_boolean(section, "config");
            bgmode = (uint8)keyfile.get_integer(section, "mode");
            Gdk.Color.parse(keyfile.get_string(section, "color"),
             out color);
            alpha = (uint8)keyfile.get_integer(section, "alpha");
            image = keyfile.get_string(section, "image");
            offset = keyfile.get_integer(section, "offset");
            max_size = keyfile.get_integer(section, "max_size");
            orient = keyfile.get_string(section, "orient");
            expand = keyfile.get_boolean(section, "expand");
        } catch {
            stderr.printf("Couldn't load configuration.\n");
        }

        // Create the socket.
        socket = new Gtk.Socket();
        add(socket);
        socket_id = (ulong)socket.get_id();

        // Determine initial orientation.
        determine_orientation(screen_position);

        // Connect signals.
        size_changed.connect(() => {
            return true;
        });
        menu_show_configure();
        configure_plugin.connect(() => {
            PrefDialog pd = new PrefDialog(this);
            pd.run();
        });
        orientation_changed.connect(() => {
            determine_orientation(screen_position);
        });
        screen_position_changed.connect(determine_orientation);
        socket.plug_removed.connect(start_dockbarx);
        notify.connect(save_config);
        save.connect(save_config);

        // Start DBX if it's been configured.
        show_all();
        if (config) start_dockbarx();
        else configure_plugin();
    }

    // Starts DBX when the plugin starts, or when the pref dialog kills it.
    public bool start_dockbarx () {
        if (!starting_dbx) {
            starting_dbx = true;
            try {
                Process.spawn_command_line_sync("pkill -f xfce4-dockbarx-plug");
            } catch {
                var d = new MessageDialog(null, 0, MessageType.ERROR,
                 ButtonsType.OK, "Failed to stop DockbarX plug.");
                d.run();
                d.destroy();
            }
            var file = lookup_rc_file();
            // Now there should be basically no reason for this to fail.
            try {
                Process.spawn_command_line_async("/usr/bin/env python2 " +
                 "/usr/share/xfce4/panel/plugins/xfce4-dockbarx-plug " +
                 @"-s $socket_id -c $file");
            } catch {
                var d = new MessageDialog(null, 0, MessageType.ERROR,
                 ButtonsType.OK, "Failed to start DockbarX plug.");
                d.run();
                d.destroy();
            }
            starting_dbx = false;
        }
        return true;
    }

    // Updates config file.
    public void save_config () {
        // Save the properties to the keyfile.
        KeyFile keyfile = new KeyFile();
        try {
            keyfile.set_boolean(section, "config", config);
            keyfile.set_integer(section, "mode", bgmode);
            keyfile.set_string(section, "color", color.to_string());
            keyfile.set_integer(section, "alpha", alpha);
            keyfile.set_string(section, "image", image);
            keyfile.set_integer(section, "offset", offset);
            keyfile.set_integer(section, "max_size", max_size);
            keyfile.set_string(section, "orient", orient);
            keyfile.set_boolean(section, "expand", expand);
            FileUtils.set_contents(save_location(true), keyfile.to_data(null));
        } catch {
            stderr.printf("Couldn't save configuration.\n");
        }
    }

    // Determines DBX orientation.
    public void determine_orientation (ScreenPosition pos) {
        switch (pos) {
        case ScreenPosition.S:
        case ScreenPosition.SE_H:
        case ScreenPosition.SW_H:
            orient = "bottom";
            break;
        case ScreenPosition.N:
        case ScreenPosition.NE_H:
        case ScreenPosition.NW_H:
            orient = "top";
            break;
        case ScreenPosition.W:
        case ScreenPosition.NW_V:
        case ScreenPosition.SW_V:
            orient = "left";
            break;
        case ScreenPosition.E:
        case ScreenPosition.NE_V:
        case ScreenPosition.SE_V:
            orient = "right";
            break;
        case ScreenPosition.FLOATING_H:
        case ScreenPosition.FLOATING_V:
        case ScreenPosition.NONE:
        default:
            // The user can orient the dock freely.
            free_orient = true;

            // Swap orientations if necessary.
            if (orientation == Orientation.HORIZONTAL) {
                if      (orient == "left")   orient = "bottom";
                else if (orient == "right")  orient = "top";
            } else if (orientation == Orientation.VERTICAL) {
                if      (orient == "bottom") orient = "left";
                else if (orient == "top")    orient = "right";
            }
            break;
        }

        // Restart DBX if it's already started.
        save_config();
        if (socket.get_plug_window() != null) {
            start_dockbarx();
        }
    }
}
