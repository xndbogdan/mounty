import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio

from share_manager import ShareManager
from ui.share_row import ShareRow
from ui.share_dialog import ShareDialog


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        
        self.share_manager = ShareManager()
        
        self.set_title("Mounty")
        self.set_default_size(900, 750)
        
        self._build_ui()
        self._load_css()
        self.refresh_shares()
    
    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        
        header = Adw.HeaderBar()
        
        add_btn = Gtk.Button()
        add_btn.set_icon_name("list-add-symbolic")
        add_btn.set_tooltip_text("Add Share")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_start(add_btn)
        
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh")
        refresh_btn.connect("clicked", lambda _: self.refresh_shares())
        header.pack_end(refresh_btn)
        
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_tooltip_text("Menu")
        
        menu = Gio.Menu()
        menu.append("About Mounty", "app.about")
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)
        
        main_box.append(header)

        self.toast_overlay = Adw.ToastOverlay()
        main_box.append(self.toast_overlay)
        self.toast_overlay.set_vexpand(True)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.toast_overlay.set_child(scrolled)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_tightening_threshold(600)
        scrolled.set_child(clamp)
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.content_box.set_margin_top(12)
        self.content_box.set_margin_bottom(12)
        clamp.set_child(self.content_box)
        
        self.share_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.content_box.append(self.share_list)
        
        self.empty_state = Adw.StatusPage()
        self.empty_state.set_icon_name("folder-remote-symbolic")
        self.empty_state.set_title("No Shares")
        self.empty_state.set_description("Click the + button to add a network share")
        self.empty_state.set_visible(False)
        self.content_box.append(self.empty_state)
        
        self._build_fstab_section()
    
    def _build_fstab_section(self):
        separator = Gtk.Separator()
        separator.set_margin_top(24)
        separator.set_margin_bottom(12)
        separator.set_margin_start(12)
        separator.set_margin_end(12)
        self.content_box.append(separator)
        
        fstab_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fstab_header.set_margin_start(12)
        fstab_header.set_margin_end(12)
        
        fstab_label = Gtk.Label(label="Automount Entries (fstab)")
        fstab_label.add_css_class("heading")
        fstab_label.set_xalign(0)
        fstab_label.set_hexpand(True)
        fstab_header.append(fstab_label)
        
        self.content_box.append(fstab_header)
        
        self.fstab_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.fstab_box.set_margin_start(12)
        self.fstab_box.set_margin_end(12)
        self.fstab_box.set_margin_top(8)
        self.content_box.append(self.fstab_box)
    
    def _load_css(self):
        css = b"""
        .card {
            background-color: alpha(@card_bg_color, 0.8);
            border-radius: 12px;
            border: 1px solid alpha(@borders, 0.5);
        }
        
        .heading { font-weight: bold; }
        .caption { font-size: 0.9em; opacity: 0.7; }
        .success { color: @success_color; }
        .error { color: @error_color; }
        .warning { color: @warning_color; }
        
        .badge {
            background-color: alpha(@success_color, 0.2);
            color: @success_color;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }
        
        .tinted-button {
            background-color: alpha(@view_fg_color, 0.1);
            border-radius: 6px;
            padding: 4px 12px;
        }
        .tinted-button:hover { background-color: alpha(@view_fg_color, 0.15); }
        
        .fstab-entry {
            font-family: monospace;
            font-size: 0.85em;
            padding: 8px 12px;
            background-color: alpha(@view_bg_color, 0.5);
            border-radius: 6px;
        }
        
        .loading-overlay {
            background-color: alpha(@window_bg_color, 0.7);
            border-radius: 12px;
        }
        """
        
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def refresh_shares(self):
        self.share_manager.load_shares()
        
        while child := self.share_list.get_first_child():
            self.share_list.remove(child)
        
        if self.share_manager.shares:
            self.empty_state.set_visible(False)
            self.share_list.set_visible(True)
            
            for share in self.share_manager.shares:
                row = ShareRow(share, self.share_manager, self)
                self.share_list.append(row)
        else:
            self.empty_state.set_visible(True)
            self.share_list.set_visible(False)
        
        self._refresh_fstab_entries()
    
    def _refresh_fstab_entries(self):
        while child := self.fstab_box.get_first_child():
            self.fstab_box.remove(child)
        
        entries = self.share_manager.get_fstab_entries()
        
        if entries:
            for entry in entries:
                label = Gtk.Label(label=entry)
                label.add_css_class("fstab-entry")
                label.set_xalign(0)
                label.set_selectable(True)
                label.set_wrap(True)
                self.fstab_box.append(label)
        else:
            no_entries = Gtk.Label(label="No Mounty entries in fstab")
            no_entries.add_css_class("dim-label")
            no_entries.set_xalign(0)
            self.fstab_box.append(no_entries)
    
    def _on_add_clicked(self, button):
        dialog = ShareDialog(self, self.share_manager)
        dialog.present(self)
    
    def show_toast(self, message: str):
        toast = Adw.Toast.new(message)
        self.toast_overlay.add_toast(toast)
