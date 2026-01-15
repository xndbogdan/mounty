import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Pango

from share_manager import Share, ShareManager


class ShareRow(Gtk.Box):
    def __init__(self, share: Share, share_manager: ShareManager, main_window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.share = share
        self.share_manager = share_manager
        self.main_window = main_window
        
        self.add_css_class("card")
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        
        self._build_ui()
        self._update_status()
    
    def _build_ui(self):
        self.overlay = Gtk.Overlay()
        self.append(self.overlay)
        
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.content.set_margin_start(16)
        self.content.set_margin_end(16)
        self.content.set_margin_top(12)
        self.content.set_margin_bottom(12)
        self.overlay.set_child(self.content)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        share_label = Gtk.Label(label=self.share.unc_path)
        share_label.set_xalign(0)
        share_label.add_css_class("heading")
        share_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        share_label.set_hexpand(True)
        top_row.append(share_label)
        
        arrow = Gtk.Label(label="→")
        arrow.add_css_class("dim-label")
        top_row.append(arrow)
        
        mount_label = Gtk.Label(label=self.share.mount_point)
        mount_label.set_xalign(1)
        mount_label.add_css_class("caption")
        mount_label.set_ellipsize(Pango.EllipsizeMode.START)
        top_row.append(mount_label)
        
        self.content.append(top_row)

        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.status_icon = Gtk.Image()
        status_row.append(self.status_icon)
        
        self.status_label = Gtk.Label()
        self.status_label.set_xalign(0)
        self.status_label.add_css_class("caption")
        self.status_label.set_hexpand(True)
        status_row.append(self.status_label)

        if self.share.automounted:
            badge = Gtk.Label(label="Automount")
            badge.add_css_class("badge")
            badge.add_css_class("success")
            status_row.append(badge)
        
        self.content.append(status_row)

        # Action buttons
        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_row.set_margin_top(4)
        
        self.test_btn = Gtk.Button(label="Test")
        self.test_btn.add_css_class("tinted-button")
        self.test_btn.connect("clicked", self._on_test)
        button_row.append(self.test_btn)
        
        self.edit_btn = Gtk.Button(label="Edit")
        self.edit_btn.add_css_class("tinted-button")
        self.edit_btn.set_sensitive(not self.share.automounted)
        self.edit_btn.connect("clicked", self._on_edit)
        button_row.append(self.edit_btn)
        
        self.mount_btn = Gtk.Button()
        self.mount_btn.add_css_class("tinted-button")
        self.mount_btn.connect("clicked", self._on_mount_toggle)
        button_row.append(self.mount_btn)
        
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        button_row.append(spacer)
        
        self.automount_btn = Gtk.Button()
        if self.share.automounted:
            self.automount_btn.set_label("Remove Automount")
            self.automount_btn.add_css_class("flat")
        else:
            self.automount_btn.set_label("Enable Automount")
            self.automount_btn.add_css_class("suggested-action")
        self.automount_btn.connect("clicked", self._on_automount_toggle)
        button_row.append(self.automount_btn)
        
        self.remove_btn = Gtk.Button(label="Remove")
        self.remove_btn.add_css_class("flat")
        self.remove_btn.add_css_class("destructive-action")
        self.remove_btn.connect("clicked", self._on_remove)
        button_row.append(self.remove_btn)
        
        self.content.append(button_row)

        self.loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.loading_box.set_halign(Gtk.Align.FILL)
        self.loading_box.set_valign(Gtk.Align.FILL)
        self.loading_box.add_css_class("loading-overlay")
        self.loading_box.set_visible(False)
        
        self.spinner = Gtk.Spinner()
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.set_valign(Gtk.Align.CENTER)
        self.spinner.set_vexpand(True)
        self.spinner.set_size_request(32, 32)
        self.loading_box.append(self.spinner)
        
        self.overlay.add_overlay(self.loading_box)
    
    def _update_status(self):
        is_mounted = self.share_manager.is_mounted(self.share)
        
        if is_mounted:
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
            self.status_icon.add_css_class("success")
            self.status_label.set_text("Mounted")
            self.mount_btn.set_label("Unmount")
        else:
            self.status_icon.set_from_icon_name("window-close-symbolic")
            self.status_icon.remove_css_class("success")
            self.status_label.set_text("Not mounted")
            self.mount_btn.set_label("Mount")
    
    def _show_message(self, message: str, is_error: bool = False):
        self.main_window.show_toast(message)
    
    def _set_loading(self, loading: bool):
        self.loading_box.set_visible(loading)
        self.spinner.set_spinning(loading)
        
        self.test_btn.set_sensitive(not loading)
        self.edit_btn.set_sensitive(not loading and not self.share.automounted)
        self.mount_btn.set_sensitive(not loading)
        self.automount_btn.set_sensitive(not loading)
        self.remove_btn.set_sensitive(not loading)
    
    def _on_test(self, button):
        self._set_loading(True)
        
        def do_test():
            success, message = self.share_manager.test_share(self.share)
            GLib.idle_add(self._on_test_complete, success, message)
        
        import threading
        thread = threading.Thread(target=do_test)
        thread.daemon = True
        thread.start()
    
    def _on_test_complete(self, success: bool, message: str):
        self._set_loading(False)
        self._show_message(message, is_error=not success)
        return False
    
    def _on_edit(self, button):
        from ui.share_dialog import ShareDialog
        dialog = ShareDialog(self.main_window, self.share_manager, self.share)
        dialog.present(self.main_window)
    
    def _on_mount_toggle(self, button):
        self._set_loading(True)
        is_mounted = self.share_manager.is_mounted(self.share)
        
        def do_mount():
            if is_mounted:
                success, message = self.share_manager.unmount_share(self.share)
            else:
                success, message = self.share_manager.mount_share(self.share)
            GLib.idle_add(self._on_mount_complete, success, message)
        
        import threading
        thread = threading.Thread(target=do_mount)
        thread.daemon = True
        thread.start()
    
    def _on_mount_complete(self, success: bool, message: str):
        self._set_loading(False)
        self._update_status()
        self._show_message(message, is_error=not success)
        return False
    
    def _on_automount_toggle(self, button):
        self._set_loading(True)
        
        def do_automount():
            if self.share.automounted:
                success, message = self.share_manager.remove_from_fstab(self.share)
            else:
                success, message = self.share_manager.add_to_fstab(self.share)
            GLib.idle_add(self._on_automount_complete, success, message)
        
        import threading
        thread = threading.Thread(target=do_automount)
        thread.daemon = True
        thread.start()
    
    def _on_automount_complete(self, success: bool, message: str):
        self._set_loading(False)
        
        if success:
            self.main_window.refresh_shares()
        else:
            self._show_message(message, is_error=True)
        return False
    
    def _on_remove(self, button):
        dialog = Adw.AlertDialog()
        dialog.set_heading("Remove Share?")
        
        if self.share.automounted:
            dialog.set_body(
                f"This will remove {self.share.unc_path} and disable its automount entry in fstab."
            )
        else:
            dialog.set_body(f"This will remove {self.share.unc_path} from your saved shares.")
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_remove_response)
        dialog.present(self.main_window)
    
    def _on_remove_response(self, dialog, response):
        if response != "remove":
            return
        
        self._set_loading(True)
        
        def do_remove():
            success, message = self.share_manager.remove_share(self.share)
            GLib.idle_add(self._on_remove_complete, success, message)
        
        import threading
        thread = threading.Thread(target=do_remove)
        thread.daemon = True
        thread.start()
    
    def _on_remove_complete(self, success: bool, message: str):
        self._set_loading(False)
        
        if success:
            self.main_window.refresh_shares()
        else:
            self._show_message(message, is_error=True)
        return False
