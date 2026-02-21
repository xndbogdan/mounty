import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

import threading

from share_manager import Share, ShareManager


class ShareDialog(Adw.Dialog):
    def __init__(self, parent: Gtk.Window, share_manager: ShareManager, share: Share = None):
        super().__init__()

        self.parent_window = parent
        self.share_manager = share_manager
        self.share = share
        self.is_edit = share is not None
        self.stack = None

        self.set_title("Edit Share" if self.is_edit else "Add Share")
        self.set_content_width(480)
        self.set_content_height(680)

        self._build_ui()

        if self.is_edit:
            self._populate_fields()
        elif self.stack:
            self._start_discovery()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(main_box)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: self.close())
        header.pack_start(cancel_btn)

        self.save_btn = Gtk.Button(label="Save")
        self.save_btn.add_css_class("suggested-action")
        self.save_btn.connect("clicked", self._on_save)
        header.pack_end(self.save_btn)

        main_box.append(header)

        # Build the manual form content
        manual_content = self._build_manual_form()

        if self.is_edit:
            # Edit mode: just the form, no stack
            main_box.append(manual_content)
        else:
            # Add mode: stack with Browse and Manual pages
            self.stack = Gtk.Stack()
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            self.stack.set_vexpand(True)

            # Browse page
            browse_page = self._build_browse_page()
            self.stack.add_titled(browse_page, "browse", "Browse")

            # Manual page
            self.stack.add_titled(manual_content, "manual", "Manual")

            # Stack switcher as title widget
            switcher = Gtk.StackSwitcher()
            switcher.set_stack(self.stack)
            header.set_title_widget(switcher)

            # Show/hide Save button based on active page
            self.save_btn.set_visible(False)
            self.stack.connect("notify::visible-child", self._on_stack_page_changed)

            main_box.append(self.stack)

    def _build_manual_form(self) -> Gtk.ScrolledWindow:
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        server_group = Adw.PreferencesGroup()
        server_group.set_title("Server Connection")
        server_group.set_description("Enter the server hostname/IP and share name separately")

        self.server_entry = Adw.EntryRow()
        self.server_entry.set_title("Server Address")
        self.server_entry.set_tooltip_text("Just the hostname or IP address (e.g., 192.168.1.100 or nas.local)")
        self.server_entry.set_text("")
        server_group.add(self.server_entry)

        self.share_entry = Adw.EntryRow()
        self.share_entry.set_title("Share Name")
        self.share_entry.set_tooltip_text("Just the share folder name (e.g., Documents, Media)")
        server_group.add(self.share_entry)

        content.append(server_group)

        cred_group = Adw.PreferencesGroup()
        cred_group.set_title("Credentials")

        self.username_entry = Adw.EntryRow()
        self.username_entry.set_title("Username")
        cred_group.add(self.username_entry)

        self.password_entry = Adw.PasswordEntryRow()
        self.password_entry.set_title("Password")
        cred_group.add(self.password_entry)

        content.append(cred_group)

        mount_group = Adw.PreferencesGroup()
        mount_group.set_title("Mount Point")

        self.mount_entry = Adw.EntryRow()
        self.mount_entry.set_title("Local Path")
        self.mount_entry.set_tooltip_text("Where to mount the share (e.g., /mnt/myshare)")

        folder_btn = Gtk.Button()
        folder_btn.set_icon_name("folder-open-symbolic")
        folder_btn.set_tooltip_text("Browse for folder")
        folder_btn.set_valign(Gtk.Align.CENTER)
        folder_btn.add_css_class("flat")
        folder_btn.connect("clicked", self._on_browse_folder)
        self.mount_entry.add_suffix(folder_btn)

        mount_group.add(self.mount_entry)
        content.append(mount_group)

        test_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        test_box.set_halign(Gtk.Align.CENTER)
        test_box.set_margin_top(12)

        self.test_btn = Gtk.Button(label="Test Connection")
        self.test_btn.add_css_class("pill")
        self.test_btn.connect("clicked", self._on_test)
        test_box.append(self.test_btn)

        self.test_spinner = Gtk.Spinner()
        test_box.append(self.test_spinner)

        content.append(test_box)

        self.status_label = Gtk.Label()
        self.status_label.set_wrap(True)
        self.status_label.set_margin_top(8)
        content.append(self.status_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(content)

        return scrolled

    def _build_browse_page(self) -> Gtk.ScrolledWindow:
        self.browse_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.browse_content.set_margin_top(24)
        self.browse_content.set_margin_bottom(24)
        self.browse_content.set_margin_start(24)
        self.browse_content.set_margin_end(24)

        # Manual server entry group
        manual_group = Adw.PreferencesGroup()
        manual_group.set_title("Add Server Manually")

        self.browse_server_entry = Adw.EntryRow()
        self.browse_server_entry.set_title("Server Address")

        browse_btn = Gtk.Button()
        browse_btn.set_icon_name("network-server-symbolic")
        browse_btn.set_tooltip_text("Browse this server")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.add_css_class("flat")
        browse_btn.connect("clicked", self._on_browse_manual_server)
        self.browse_server_entry.add_suffix(browse_btn)
        self.browse_server_entry.connect("entry-activated", lambda _: self._on_browse_manual_server(None))

        manual_group.add(self.browse_server_entry)
        self.browse_content.append(manual_group)

        # Network servers group
        self.servers_group = Adw.PreferencesGroup()
        self.servers_group.set_title("Network Servers")
        self.browse_content.append(self.servers_group)

        # Discovery status row (spinner + label)
        self.discovery_status_row = Adw.ActionRow()
        self.discovery_status_row.set_title("Discovering servers...")
        self.discovery_spinner = Gtk.Spinner()
        self.discovery_spinner.set_valign(Gtk.Align.CENTER)
        self.discovery_status_row.add_prefix(self.discovery_spinner)
        self.servers_group.add(self.discovery_status_row)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.browse_content)

        return scrolled

    def _on_stack_page_changed(self, stack, pspec):
        is_manual = stack.get_visible_child_name() == "manual"
        self.save_btn.set_visible(is_manual)

    def switch_to_manual(self):
        if self.stack:
            self.stack.set_visible_child_name("manual")

    # -- Browse page logic --

    def _start_discovery(self):
        self.discovery_spinner.start()

        def do_discover():
            success, result = self.share_manager.discover_servers()
            GLib.idle_add(self._on_discovery_complete, success, result)

        thread = threading.Thread(target=do_discover)
        thread.daemon = True
        thread.start()

    def _on_discovery_complete(self, success, result):
        self.discovery_spinner.stop()
        self.servers_group.remove(self.discovery_status_row)

        if success:
            for server_info in result:
                self._add_server_expander(server_info["address"], server_info["name"])
        else:
            status_row = Adw.ActionRow()
            status_row.set_title(result)
            status_row.add_css_class("dim-label")
            self.servers_group.add(status_row)

        return False

    def _on_browse_manual_server(self, button):
        address = self.browse_server_entry.get_text().strip()
        if not address:
            return
        self._add_server_expander(address, address)
        self.browse_server_entry.set_text("")

    def _add_server_expander(self, address, name):
        expander = Adw.ExpanderRow()
        if name and name != address:
            expander.set_title(f"{name} ({address})")
        else:
            expander.set_title(address)
        expander.set_subtitle("Click to browse shares")

        # Store data on the widget
        expander._server_address = address
        expander._loaded = False
        expander._cred_widgets = None

        expander.connect("notify::expanded", self._on_server_expanded)
        self.servers_group.add(expander)

    def _on_server_expanded(self, expander, pspec):
        if not expander.get_expanded() or expander._loaded:
            return
        expander._loaded = True

        address = expander._server_address

        # Add spinner row
        spinner_row = Adw.ActionRow()
        spinner_row.set_title("Scanning shares...")
        spinner = Gtk.Spinner()
        spinner.start()
        spinner.set_valign(Gtk.Align.CENTER)
        spinner_row.add_prefix(spinner)
        expander.add_row(spinner_row)

        # Check for existing credentials from saved shares
        username, password = "", ""
        for s in self.share_manager.shares:
            if s.server == address:
                username, password = s.username, s.password
                break

        def do_scan():
            success, result = self.share_manager.scan_shares(address, username, password)
            GLib.idle_add(self._on_scan_complete, expander, spinner_row, success, result, username, password)

        thread = threading.Thread(target=do_scan)
        thread.daemon = True
        thread.start()

    def _on_scan_complete(self, expander, spinner_row, success, result, username, password):
        expander.remove(spinner_row)

        if success:
            self._show_shares_in_expander(expander, result, username, password)
        elif result == "auth_error":
            self._show_auth_form(expander)
        else:
            error_row = Adw.ActionRow()
            error_row.set_title(result)
            error_row.add_css_class("error")
            expander.add_row(error_row)

        return False

    def _show_shares_in_expander(self, expander, shares, username, password):
        address = expander._server_address

        # Remove any existing credential widgets
        if expander._cred_widgets:
            for w in expander._cred_widgets:
                expander.remove(w)
            expander._cred_widgets = None

        for share_info in shares:
            row = Adw.ActionRow()
            row.set_title(share_info["name"])
            if share_info.get("comment"):
                row.set_subtitle(share_info["comment"])
            row.set_activatable(True)

            icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
            icon.set_valign(Gtk.Align.CENTER)
            row.add_suffix(icon)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))

            row._share_name = share_info["name"]
            row._server_address = address
            row._username = username
            row._password = password
            row.connect("activated", self._on_share_row_activated)

            expander.add_row(row)

        expander.set_subtitle(f"{len(shares)} share{'s' if len(shares) != 1 else ''}")

    def _show_auth_form(self, expander):
        auth_user = Adw.EntryRow()
        auth_user.set_title("Username")
        expander.add_row(auth_user)

        auth_pass = Adw.PasswordEntryRow()
        auth_pass.set_title("Password")
        expander.add_row(auth_pass)

        connect_row = Adw.ActionRow()
        connect_row.set_title("Connect")
        connect_row.set_activatable(True)
        connect_icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
        connect_icon.set_valign(Gtk.Align.CENTER)
        connect_row.add_suffix(connect_icon)
        expander.add_row(connect_row)

        expander._cred_widgets = [auth_user, auth_pass, connect_row]

        def on_connect(row):
            user = auth_user.get_text().strip()
            pwd = auth_pass.get_text()
            address = expander._server_address

            # Replace connect row with spinner
            expander.remove(connect_row)
            spinner_row = Adw.ActionRow()
            spinner_row.set_title("Connecting...")
            spinner = Gtk.Spinner()
            spinner.start()
            spinner.set_valign(Gtk.Align.CENTER)
            spinner_row.add_prefix(spinner)
            expander.add_row(spinner_row)
            expander._cred_widgets.append(spinner_row)

            def do_scan():
                success, result = self.share_manager.scan_shares(address, user, pwd)
                GLib.idle_add(on_connect_complete, success, result, user, pwd, spinner_row)

            thread = threading.Thread(target=do_scan)
            thread.daemon = True
            thread.start()

        def on_connect_complete(success, result, user, pwd, spinner_row):
            expander.remove(spinner_row)

            if success:
                self._show_shares_in_expander(expander, result, user, pwd)
            else:
                # Re-add connect row and show error
                expander.add_row(connect_row)
                expander._cred_widgets = [auth_user, auth_pass, connect_row]

                error_row = Adw.ActionRow()
                error_row.set_title("Authentication failed" if result == "auth_error" else result)
                error_row.add_css_class("error")
                expander.add_row(error_row)
                # Auto-remove error after 3 seconds
                GLib.timeout_add(3000, lambda: expander.remove(error_row) or False)

            return False

        connect_row.connect("activated", on_connect)

    def _on_share_row_activated(self, row):
        self.server_entry.set_text(row._server_address)
        self.share_entry.set_text(row._share_name)
        if row._username:
            self.username_entry.set_text(row._username)
        if row._password:
            self.password_entry.set_text(row._password)
        self.mount_entry.set_text(f"/mnt/{row._share_name.lower()}")
        self.switch_to_manual()

    # -- Existing methods --

    def _populate_fields(self):
        self.server_entry.set_text(self.share.server)
        self.share_entry.set_text(self.share.share_name)
        self.username_entry.set_text(self.share.username)
        self.password_entry.set_text(self.share.password)
        self.mount_entry.set_text(self.share.mount_point)

    def _on_browse_folder(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Mount Point")
        dialog.set_modal(True)

        current_path = self.mount_entry.get_text().strip()
        from gi.repository import Gio
        if current_path and current_path.startswith('/'):
            try:
                dialog.set_initial_folder(Gio.File.new_for_path(current_path))
            except Exception:
                dialog.set_initial_folder(Gio.File.new_for_path("/mnt"))
        else:
            dialog.set_initial_folder(Gio.File.new_for_path("/mnt"))

        dialog.select_folder(self.parent_window, None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.mount_entry.set_text(folder.get_path())
        except Exception:
            pass  # User cancelled

    def _get_share_from_fields(self) -> Share:
        share_id = self.share.id if self.is_edit else self.share_manager.generate_id()
        automounted = self.share.automounted if self.is_edit else False

        server = self._sanitize_server(self.server_entry.get_text().strip())
        share_name = self._sanitize_share_name(self.share_entry.get_text().strip())

        return Share(
            id=share_id,
            server=server,
            share_name=share_name,
            username=self.username_entry.get_text().strip(),
            password=self.password_entry.get_text(),
            mount_point=self.mount_entry.get_text().strip(),
            automounted=automounted
        )

    def _sanitize_server(self, server: str) -> str:
        import re
        server = re.sub(r'^(smb|cifs|file|https?):/*', '', server, flags=re.IGNORECASE)
        if '@' in server:
            server = server.split('@')[-1]
        server = server.split('/')[0]
        server = server.split(':')[0]
        return server.strip()

    def _sanitize_share_name(self, share_name: str) -> str:
        return share_name.strip('/')

    def _validate(self) -> tuple[bool, str]:
        server = self._sanitize_server(self.server_entry.get_text().strip())
        share_name = self._sanitize_share_name(self.share_entry.get_text().strip())

        if not server:
            return False, "Server address is required"
        if not share_name:
            return False, "Share name is required"
        if not self.mount_entry.get_text().strip():
            return False, "Mount point is required"
        if not self.mount_entry.get_text().strip().startswith('/'):
            return False, "Mount point must be an absolute path"
        return True, ""

    def _check_mount_conflicts(self) -> tuple[str, str]:
        mount_point = self.mount_entry.get_text().strip().rstrip('/')
        current_id = self.share.id if self.is_edit else None

        for share in self.share_manager.shares:
            if share.id == current_id:
                continue

            existing_mount = share.mount_point.rstrip('/')
            if existing_mount == mount_point:
                is_mounted = self.share_manager.is_mounted(share)

                if is_mounted:
                    return 'error', f"Mount point already in use and currently mounted ({share.unc_path})"
                elif share.automounted:
                    return 'error', f"Mount point has automount enabled ({share.unc_path})"
                else:
                    return 'warning', f"Another share uses this mount point ({share.unc_path})"

        return 'ok', ""

    def _set_status(self, message: str, is_error: bool = False, is_warning: bool = False):
        self.status_label.set_text(message)

        self.status_label.remove_css_class("error")
        self.status_label.remove_css_class("success")
        self.status_label.remove_css_class("warning")

        if is_error:
            self.status_label.add_css_class("error")
        elif is_warning:
            self.status_label.add_css_class("warning")
        else:
            self.status_label.add_css_class("success")

    def _on_test(self, button):
        valid, msg = self._validate()
        if not valid:
            self._set_status(msg, is_error=True)
            return

        self.test_btn.set_sensitive(False)
        self.test_spinner.start()
        self.status_label.set_text("Testing connection...")

        share = self._get_share_from_fields()

        def do_test():
            success, message = self.share_manager.test_share(share)
            GLib.idle_add(self._on_test_complete, success, message)

        thread = threading.Thread(target=do_test)
        thread.daemon = True
        thread.start()

    def _on_test_complete(self, success: bool, message: str):
        self.test_btn.set_sensitive(True)
        self.test_spinner.stop()
        self._set_status(message, is_error=not success)
        return False

    def _on_save(self, button):
        valid, msg = self._validate()
        if not valid:
            self._set_status(msg, is_error=True)
            return

        conflict_level, conflict_msg = self._check_mount_conflicts()
        if conflict_level == 'error':
            self._set_status(conflict_msg, is_error=True)
            return
        elif conflict_level == 'warning':
            self._set_status(f"Warning: {conflict_msg}", is_warning=True)

        share = self._get_share_from_fields()

        self.save_btn.set_sensitive(False)
        self.test_spinner.start()
        self.status_label.set_text("Testing connection before saving...")

        def do_test_and_save():
            success, message = self.share_manager.test_share(share)
            GLib.idle_add(self._on_save_test_complete, success, message, share)

        thread = threading.Thread(target=do_test_and_save)
        thread.daemon = True
        thread.start()

    def _on_save_test_complete(self, success: bool, message: str, share: Share):
        self.save_btn.set_sensitive(True)
        self.test_spinner.stop()

        if not success:
            self._set_status(f"Cannot save: {message}", is_error=True)
            return False

        if self.is_edit:
            self.share_manager.update_share(share)
        else:
            self.share_manager.add_share(share)

        if hasattr(self.parent_window, 'refresh_shares'):
            self.parent_window.refresh_shares()

        self.close()
        return False
