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
using Xfconf;
using Gtk;


// xfce4-panel uses this to register the plugin.
[ModuleInit]
public Type xfce_panel_module_init (TypeModule module) {
    return typeof (DockbarXPlugin);
}

public class DockbarXPlugin : PanelPlugin {
    private Gtk.Socket   socket;
    private ulong        socket_id;
    private bool         starting_dbx = false;
    public  int          bgmode      { get; set; }
    public  string       color       { get; set; }
    public  int          alpha       { get; set; }
    public  string       image       { get; set; }
    public  int          offset      { get; set; }
    public  int          max_size    { get; set; }
    public  string       orient      { get; set; }
    public  bool         free_orient { get; set; }
    private bool         _block_ah = false;
    public  Channel      xfc;
    public  string       prop;
    
    // This inhibits autohide whenever xfconf says to.
    public bool block_ah {
        get { return _block_ah; } 
        set { block_autohide(_block_ah = value); }
    }

    public override void @construct () {
        // This program does one thing, and one thing only:
        // Embeds the already-made DockBarX using the helper
        // application, xfce4-dockbarx-plug.
        
        Xfconf.init();
        xfc = new Channel.with_property_base("xfce4-panel",get_property_base());
        
        bgmode = xfc.get_int("/bgmode", 2);
        color = xfc.get_string("/color", "#000");
        alpha = xfc.get_int("/alpha", 100);
        image = xfc.get_string("/image", "");
        offset = xfc.get_int("/offset", 0);
        max_size = xfc.get_int("/max-size", 0);
        orient = xfc.get_string("/orient", "bottom");
        expand = xfc.get_bool("/expand", false);
        block_ah = xfc.get_bool("/block-autohide", false);
        
        Property.bind(xfc, "/mode", typeof(int), this, "bgmode");
        Property.bind(xfc, "/color", typeof(string), this, "color");
        Property.bind(xfc, "/alpha", typeof(int), this, "alpha");
        Property.bind(xfc, "/image", typeof(string), this, "image");
        Property.bind(xfc, "/offset", typeof(int), this, "offset");
        Property.bind(xfc, "/max-size", typeof(int), this, "max-size");
        Property.bind(xfc, "/orient", typeof(string), this, "orient");
        Property.bind(xfc, "/expand", typeof(bool), this, "expand");
        Property.bind(xfc, "/block-autohide", typeof(bool), this, "block_ah");

        socket = new Gtk.Socket();
        add(socket);
        socket_id = (ulong)socket.get_id();
        determine_orientation(screen_position);
        size_changed.connect(() => { return true; });
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

        show_all();
        start_dockbarx();
    }

    // Starts DBX when the plugin starts, or when something kills it.
    public bool start_dockbarx () {
        if (!starting_dbx) {
            starting_dbx = true;
            try {
                Process.spawn_command_line_sync(
                 "pkill -f 'python.*xfce4-dockbarx-plug'");
            } catch {
                var d = new MessageDialog(null, 0, MessageType.ERROR,
                 ButtonsType.OK, "Failed to stop DockbarX plug.");
                d.run();
                d.destroy();
            }
            // There should be basically no reason for this to fail.
            try {
                Process.spawn_command_line_async("/usr/bin/env python2 " +
                 "/usr/share/xfce4/panel/plugins/xfce4-dockbarx-plug " +
                 @"-s $socket_id -i $unique_id");
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

        // We have to restart DBX on orientation change because the
        // plug doesn't handle it properly yet.
        if (socket.get_plug_window() != null) {
            start_dockbarx();
        }
    }
}
