#!/usr/bin/env python3

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from ui.main_window import MainWindow


class MountyApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.mounty.NetworkShareManager",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        
        GLib.set_application_name("Mounty")
    
    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(self)
        win.present()
    
    def do_startup(self):
        Adw.Application.do_startup(self)
        
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)
        
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Ctrl>q"])
    
    def _on_about(self, action, param):
        about = Adw.AboutDialog()
        about.set_application_name("Mounty")
        about.set_version("1.0.0")
        about.set_developer_name("Mounty Project")
        about.set_license_type(Gtk.License.MIT_X11)
        about.set_comments("A Linux application for managing network shares with fstab integration.")
        about.set_website("https://github.com/example/mounty")
        about.set_application_icon("mounty")
        
        about.present(self.props.active_window)


def main():
    app = MountyApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
