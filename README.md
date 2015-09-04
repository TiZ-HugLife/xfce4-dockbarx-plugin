# xfce4-dockbarx-plugin
### ver. 0.4.1

## About xfce4-dockbarx-plugin
xfce4-dockbarx-plugin is free software. Please see the file COPYING for details. For building and installation instructions please see the INSTALL file. For information on the authors of this program, see AUTHORS and THANKS.

xfce4-dockbarx-plugin is a pair of programs--a gtk socket in Vala and a gtk plug in Python--that work together to embed DockbarX into xfce4-panel. See THANKS for details on DockbarX. Because this is not a port and just grabs the pre-existing DockbarX, you immediately benefit from any updates made to DBX, and already have all the pre-existing functionality.

## Using xfce4-dockbarx-plugin
The old version of this plugin tried to blend in with the panel, and due to limitations with the Vala bindings for Xfconf, could only blend in with panel-0. You were pretty much out of luck if panel-0 didn't exist. The new version uses manual configuration to determine background styling.

When you first start the plugin, a dialog will appear that will allow you to configure the way the background is drawn. You can then configure it to blend in with the panel it's on... or you can even choose for it *not* to blend in! Since you can choose for it not to blend in, you can also expand it if you want. The plugin will automatically detect panel orientation and screen position, and will save that to the config file, which is shared between both the socket and the plug. Whenever the configuration is changed, the plug is restarted.

You can avoid having to manually configure your background by using the panel blend mode, new and default as of 0.4. This makes use of xfconf's dbus interface and python-dbus to retrieve information about the panel background, and also connects to a signal and update it whenever it changes. However, there is still one gotcha; namely, if you use the image style, you still need to make sure the offset is properly configured if you have an image that necessitates it.

## Any extras?
This plugin includes a DockbarX theme called Mouse, created by me for use with xfce4-panel (but should work fine on Gnome/Mate panels, AWN, or DockX). There are two variant versions for varying levels of x/ythickness on the panel widgets to make them match up nicely. If a theme gives different panel widgets differing x/ythickness, its author is a sick bastard.

## Okay, I'm sold! Gimme the goods!
Some distros already have it packaged in some form:
* Arch Linux / Manjaro users can install from the [AUR](https://aur.archlinux.org/packages/xfce4-dockbarx-plugin/).
* Ubuntu users can install from the [Dockbar PPA](https://launchpad.net/~dockbar-main/+archive/ppa).
* The stable source release can be found on [Xfce-Look](http://xfce-look.org/content/show.php?content=157865).

If you want to (or have to) install from source, you need the following dependencies:

* Vala >= 0.12
* GLib >= 2.10
* GTK+2 >= 2.16
* Xfce4-Panel >= 4.8
* DockbarX >= 0.49

To configure, build, and install, run these commands:

    ./waf configure
    ./waf build
    sudo ./waf install

The panel will probably not detect the plugin unless you install it in the /usr prefix, so instead do the configure step with `./waf configure --prefix=/usr` If you are using a distribution that supports checkinstall, you can replace the install step with `sudo ./waf checkinstall` to install it in your package manager.

## Awesome! Who do I need to thank for all this?
* Aleksey Shaferov is the original Dockbar developer.
* Matias Särs is the developer of the DockbarX fork.
* The included Vala bindings were developed by Mike Masonnet.
* The developers of the Vala and Python languages are to be thanked, of course.
* The build system is waf, so all the guys working on that are to thank for keeping this out of autohell.
* Trent McPheron is the original developer of this beautifully hacky xfce4 panel plugin that really should not work as well as it does.
* And the github community to whom I entrust the future of this plugin.

## I want to make the plugin better!
Awesome! Fork the repo and send me pull requests! I will probably merge any request I get. The future of this plugin is in your hands now. :)
