#!/usr/bin/env python2
#
# Copyright (c) 2011- Trent McPheron <twilightinzero@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# For creating a source archive.
APPNAME = 'xfce4-dockbarx-plugin'
VERSION = '0.4.1'

# Required waf stuff.
top = '.'
out = 'build'

def options (ctx):
    ctx.load('compiler_c')
    ctx.load('vala')

def configure (ctx):
    # Strip extraneous slash from prefix.
    if ctx.options.prefix[-1] == '/' :
        ctx.options.prefix += ctx.options.prefix[-1]

    # Check for required stuff.
    ctx.load('compiler_c misc')
    ctx.load('vala', funs='')
    ctx.check_vala()
    args = '--cflags --libs'
    ctx.find_program('dockx')
    ctx.check_cfg(package = 'glib-2.0', atleast_version = '2.10',
        uselib_store = 'GLIB', mandatory = True, args = args)
    ctx.check_cfg(package = 'gtk+-2.0', atleast_version = '2.16',
        uselib_store = 'GTK', mandatory = True, args = args)
    ctx.check_cfg(package = 'libxfce4panel-1.0', atleast_version = '4.8',
        uselib_store = 'XFCE4PANEL', mandatory = True, args = args)

def build (ctx):
    # Compile the program.
    ctx.program(
        features     = 'c cshlib',
        is_lib       = True,
        vapi_dirs    = 'vapi',
        source       = ctx.path.ant_glob('src/*.vala'),
        packages     = 'glib-2.0 gtk+-2.0 libxfce4panel-1.0',
        target       = 'dockbarx',
        install_path = '${PREFIX}/lib/xfce4/panel/plugins/',
        uselib       = 'GLIB GTK XFCE4PANEL')

    # Install other files.
    ctx(
        features = 'subst',
        source = 'data/dockbarx.desktop.in',
        target = 'data/dockbarx.desktop')
    ctx.install_files(
        '${PREFIX}/share/xfce4/panel/plugins/',
        'data/dockbarx.desktop')
    ctx.install_files(
        '${PREFIX}/share/dockbarx/themes/',
        'data/Mouse.tar.gz')
    ctx.install_files(
        '${PREFIX}/share/dockbarx/themes/',
        'data/Mouse-4.tar.gz')
    ctx.install_files(
        '${PREFIX}/share/dockbarx/themes/',
        'data/Mouse-6.tar.gz')
    ctx.install_files(
        '${PREFIX}/share/dockbarx/themes/',
        'data/MouseNeo.tar.gz')
    ctx.install_files(
        '${PREFIX}/share/dockbarx/themes/',
        'data/MouseNeo-4.tar.gz')
    ctx.install_files(
        '${PREFIX}/share/dockbarx/themes/',
        'data/MouseNeo-6.tar.gz')
    ctx.install_as(
        '/usr/share/xfce4/panel/plugins/xfce4-dockbarx-plug',
        'src/xfce4-dockbarx-plug.py',
        chmod=0o755)

def checkinstall (ctx):
    ctx.exec_command('checkinstall' +
     ' --pkgname=' + APPNAME + ' --pkgversion=' + VERSION +
     ' --provides=' + APPNAME + ' --requires=dockbarx' +
     ' --deldoc=yes --deldesc=yes --delspec=yes --backup=no' +
     ' --exclude=/home -y ./waf install')
