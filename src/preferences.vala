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

using Gtk;


class PrefDialog : Dialog {

    private DockbarXPlugin    plugin;
    private RadioButton       bottom_radio;
    private RadioButton       top_radio;
    private RadioButton       color_radio;
    private RadioButton       image_radio;
    private RadioButton       blend_radio;
    private ColorButton       color_button;
    private HScale            alpha_scale;
    private FileChooserButton image_button;
    private SpinButton        offset_spin;
    private SpinButton        max_size_spin;
    private CheckButton       expand_check;

    public PrefDialog (DockbarXPlugin plugin) {
        // Preliminary stuff.
        this.plugin = plugin;
        title = "DockbarX Preferences";
        response.connect((i) => {
            if (i == ResponseType.APPLY) {
                plugin.start_dockbarx();
            } else {
                destroy();
            }
        });

        // Make some actual wiggits.
        unowned VBox content = get_content_area() as VBox;
        content.spacing = 12;

        // Let's get our fields out of the way first.
        color_radio = new RadioButton.with_label(null, "Solid color");
        image_radio = new RadioButton.with_label_from_widget(
         color_radio, "Background image");
        blend_radio = new RadioButton.with_label_from_widget(
         image_radio, "Blend with panel");
        color_button = new ColorButton();
        alpha_scale = new HScale.with_range(0, 100, 1);
        alpha_scale.value_pos = PositionType.RIGHT;
        image_button = new FileChooserButton("Select background image",
         FileChooserAction.OPEN);
        offset_spin = new SpinButton.with_range(-4096, 4096, 1);
        max_size_spin = new SpinButton.with_range(0, 4096, 1);
        expand_check = new CheckButton.with_label("Expand");

        // Bottom/Top change to Left/Right if the panel's vertical.
        var lab1 = "Bottom";
        var lab2 = "Top";
        if (plugin.orientation == Orientation.VERTICAL) {
            lab1 = "Left";
            lab2 = "Right";
        }
        bottom_radio = new RadioButton.with_label(null, lab1);
        top_radio = new RadioButton.with_label_from_widget(bottom_radio, lab2);

        // Now let's make the other stuff.
        var orient_frame = new Frame("Orientation");
        var color_frame = new Frame(null);
        color_frame.label_widget = color_radio;
        var image_frame = new Frame(null);
        image_frame.label_widget = image_radio;

        // Assemble the orientation frame.
        var orient_box = new HBox(false, 8);
        orient_box.pack_start(bottom_radio, true, true);
        orient_box.pack_start(top_radio, true, true);
        orient_frame.add(orient_box);

        // Assemble the color frame.
        var color_table = new Table(2, 2, false);
        color_table.column_spacing = 8;
        var color_label = new Label("Color:");
        var alpha_label = new Label("Alpha:");
        color_table.attach(color_label, 0, 1, 0, 1, 0, 0, 0, 0);
        color_table.attach(alpha_label, 0, 1, 1, 2, 0, 0, 0, 0);
        color_table.attach(color_button, 1, 2, 0, 1, AttachOptions.EXPAND |
         AttachOptions.FILL, 0, 0, 0);
        color_table.attach(alpha_scale, 1, 2, 1, 2, AttachOptions.EXPAND |
         AttachOptions.FILL, 0, 0, 0);
        color_frame.add(color_table);

        // Assemble the image frame.
        var image_table = new Table(2, 2, false);
        image_table.column_spacing = 8;
        var image_label = new Label("Image:");
        var offset_label = new Label("Offset:");
        image_table.attach(image_label, 0, 1, 0, 1, 0, 0, 0, 0);
        image_table.attach(offset_label, 0, 1, 1, 2, 0, 0, 0, 0);
        image_table.attach(image_button, 1, 2, 0, 1, AttachOptions.EXPAND |
         AttachOptions.FILL, 0, 0, 0);
        image_table.attach(offset_spin, 1, 2, 1, 2, AttachOptions.EXPAND |
         AttachOptions.FILL, 0, 0, 0);
        image_frame.add(image_table);
        
        // Asseemble the size box.
        var size_box = new HBox(false, 2);
        size_box.pack_start(new Label("Max size:"));
        size_box.pack_start(max_size_spin);
        size_box.pack_start(expand_check);

        // Put it all together.
        if (!plugin.free_orient) {
            content.pack_start(orient_frame);
        }
        content.pack_start(blend_radio);
        content.pack_start(color_frame);
        content.pack_start(image_frame);
        content.pack_start(size_box);

        // Add some buttons.
        add_button(Stock.APPLY, ResponseType.APPLY);
        add_button(Stock.CLOSE, ResponseType.CLOSE);

        // Set initial values.
        bottom_radio.active = plugin.orient == "bottom" ||
         plugin.orient == "left";
        top_radio.active = plugin.orient == "top" || plugin.orient == "right";
        color_radio.active = plugin.bgmode == 0;
        image_radio.active = plugin.bgmode == 1;
        blend_radio.active = plugin.bgmode == 2;
        Gdk.Color color;
        Gdk.Color.parse(plugin.color, out color);
        color_button.color = color;
        alpha_scale.set_value(plugin.alpha);
        image_button.set_filename(plugin.image);
        offset_spin.value = plugin.offset;
        expand_check.active = plugin.expand;

        // Signals, yo.
        bottom_radio.toggled.connect(() => {
            if (plugin.orientation == Orientation.HORIZONTAL) {
                plugin.orient = bottom_radio.active ? "bottom" : "top";
            } else {
                plugin.orient = bottom_radio.active ? "left" : "right";
            }
        });
        top_radio.toggled.connect(() => {
            if (plugin.orientation == Orientation.HORIZONTAL) {
                plugin.orient = top_radio.active ? "top" : "bottom";
            } else {
                plugin.orient = top_radio.active ? "right" : "left";
            }
        });
        color_radio.toggled.connect(() => {
            plugin.bgmode = color_radio.active ? 0 : blend_radio.active ? 2 : 1;
        });
        image_radio.toggled.connect(() => {
            plugin.bgmode = image_radio.active ? 1 : blend_radio.active ? 2 : 0;
        });
        blend_radio.toggled.connect(() => {
            plugin.bgmode = blend_radio.active ? 2 : color_radio.active ? 0 : 1;
        });
        color_button.color_set.connect(() => {
            plugin.color = color_button.color.to_string();
        });
        alpha_scale.value_changed.connect(() => {
            plugin.alpha = (uint8)alpha_scale.get_value();
        });
        image_button.file_set.connect(() => {
            plugin.image = image_button.get_filename();
        });
        offset_spin.value_changed.connect(() => {
            plugin.offset = (int)offset_spin.value;
        });
        max_size_spin.value_changed.connect(() => {
            plugin.max_size = (int)max_size_spin.value;
        });
        expand_check.toggled.connect(() => {
            plugin.expand = expand_check.active;
        });

        // Get the show on the road.
        show_all();
    }
}
