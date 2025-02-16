import gi
import subprocess
import threading
import time
import os
import json
from gi.repository import Gtk, GLib, GdkPixbuf, Notify

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')

# Detect if we are on Wayland or X11
def detect_graphics_backend():
    session_type = os.getenv('XDG_SESSION_TYPE', '').lower()

    if session_type == 'wayland':
        print("Detected Wayland")
    else:
        print("Detected X11, using X11 backend")
        os.environ['GDK_BACKEND'] = 'x11'

detect_graphics_backend()

# Read the list of applications from a JSON file
def load_applications(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

CATEGORIES = load_applications('/usr/share/patchy/apps/applications_en.json')

class SoftwareBoutique(Gtk.Window):
    def __init__(self):
        super().__init__(title="Patchy")
        self.set_default_size(640, 400)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(True)
        self.connect("destroy", Gtk.main_quit)

        current_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(current_dir, "/usr/share/patchy/patc.svg")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

        Notify.init("Patchy")

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)
        self.create_command_bar(main_box)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        scrolled_window.add(self.notebook)
        main_box.pack_start(scrolled_window, True, True, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_no_show_all(True)
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.connect("clicked", self.cancel_installation)
        self.cancel_button.set_no_show_all(True)

        self.action_button = Gtk.Button(label="Install/Uninstall Selected Packages (0)")
        self.action_button.set_sensitive(False)
        self.action_button.connect("clicked", self.action_selected_packages)

        progress_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        progress_box.pack_start(self.progress_bar, True, True, 10)
        progress_box.pack_end(self.cancel_button, False, False, 10)

        main_box.pack_start(progress_box, False, False, 10)
        main_box.pack_start(self.action_button, False, False, 10)

        self.populate_notebook()
        self.selected_packages = []
        self.selected_for_install = []
        self.selected_for_uninstall = []

        self.activity = None
        self._stop_event = threading.Event()

    def create_command_bar(self, parent_box):
        menubar = Gtk.MenuBar()
        help_menu = Gtk.Menu()
        about_item = Gtk.MenuItem(label="About")
        about_item.connect("activate", self.show_about_dialog)
        help_menu.append(about_item)

        store_menu = Gtk.Menu()
        open_bauh_item = Gtk.MenuItem(label="Open Bauh")
        open_bauh_item.connect("activate", self.open_bauh)
        store_menu.append(open_bauh_item)

        update_item = Gtk.MenuItem(label="Update Application List")
        update_item.connect("activate", self.update_app_list)
        store_menu.append(update_item)

        store_menu_item = Gtk.MenuItem(label="Store")
        store_menu_item.set_submenu(store_menu)
        menubar.append(store_menu_item)

        help_menu_item = Gtk.MenuItem(label="Help")
        help_menu_item.set_submenu(help_menu)
        menubar.append(help_menu_item)
        parent_box.pack_start(menubar, False, False, 0)

    def populate_notebook(self):
        self.app_boxes = {}
        for category, apps in CATEGORIES.items():
            tab_label = Gtk.Label(label=category)
            category_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
            for app in apps:
                app_box = self.create_app_box(app)
                self.app_boxes[app["command"]] = app_box
                category_box.pack_start(app_box, False, False, 0)
            self.notebook.append_page(category_box, tab_label)
        self.update_all_app_statuses()

    def create_app_box(self, app):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Path to the local icons folder
        current_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(current_dir, "/usr/share/patchy/icons", f"{app['icon']}.svg")

        if os.path.exists(icon_path):
            icon = Gtk.Image.new_from_file(icon_path)
        else:
            icon = Gtk.Image.new_from_icon_name("image-missing", Gtk.IconSize.DIALOG)

        label = Gtk.Label(label=f"<b>{app['name']}</b>\n{app['description']}", use_markup=True)
        label.set_xalign(0)

        checkbox = Gtk.CheckButton()
        checkbox.connect("toggled", self.on_checkbox_toggled, app["command"])
        box.pack_start(checkbox, False, False, 0)
        box.pack_start(icon, False, False, 0)
        box.pack_start(label, True, True, 0)

        installed_label = Gtk.Label(label="", use_markup=True)
        box.pack_end(installed_label, False, False, 0)

        return box

    def is_installed(self, command):
        # Check if the program binary exists in the common paths
        paths = os.getenv('PATH', '').split(os.pathsep)
        for path in paths:
            if os.path.exists(os.path.join(path, command)):
                print(f"'{command}' found in {path}")
                return True

        # Check if the package is installed with dpkg -l
        try:
            result = subprocess.run(['dpkg-query', '-W', '-f=${Status}', command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0 and 'install ok installed' in result.stdout.decode():
                print(f"'{command}' is installed (verified with dpkg)")
                return True
        except subprocess.CalledProcessError:
            pass

        print(f"'{command}' is not installed")
        return False

    def on_checkbox_toggled(self, checkbox, command):
        self.show_progress_bar("Checking status...")  # Show progress bar

        def check_installed_status():
            if checkbox.get_active():
                if command not in self.selected_packages:
                    self.selected_packages.append(command)
                    if command in self.selected_for_uninstall or command in self.selected_for_install:
                        GLib.idle_add(self.update_action_button)
                        GLib.idle_add(self.hide_progress_bar)
                        return
                    if self.is_installed(command):
                        self.selected_for_uninstall.append(command)
                    else:
                        self.selected_for_install.append(command)
            else:
                if command in self.selected_packages:
                    self.selected_packages.remove(command)
                if command in self.selected_for_uninstall:
                    self.selected_for_uninstall.remove(command)
                if command in self.selected_for_install:
                    self.selected_for_install.remove(command)

            GLib.idle_add(self.update_action_button)
            GLib.idle_add(self.hide_progress_bar)  # Hide progress bar

        threading.Thread(target=check_installed_status).start()

    def show_progress_bar(self, text):
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_text(text)
        self.progress_bar.show()

        # Start the progress bar in activity mode
        self.progress_bar.pulse()
        self.activity = GLib.timeout_add(100, self.progress_bar.pulse)

    def hide_progress_bar(self):
        if self.activity:
            GLib.source_remove(self.activity)
            self.activity = None
        self.progress_bar.hide()

    def update_action_button(self):
        num_selected_install = len(self.selected_for_install)
        num_selected_uninstall = len(self.selected_for_uninstall)

        if num_selected_install > 0 and num_selected_uninstall == 0:
            self.action_button.set_label(f"Install Selected Packages ({num_selected_install})")
            self.action_button.set_sensitive(True)
        elif num_selected_uninstall > 0 and num_selected_install == 0:
            self.action_button.set_label(f"Uninstall Selected Packages ({num_selected_uninstall})")
            self.action_button.set_sensitive(True)
        else:
            self.action_button.set_label("Install/Uninstall Selected Packages (0)")
            self.action_button.set_sensitive(False)

        # Enable only the installed applications for uninstalling and the non-installed ones for installing
        for cmd, box in self.app_boxes.items():
            app_checkbox = box.get_children()[0]
            app_installed = self.is_installed(cmd)

            if num_selected_install > 0:
                app_checkbox.set_sensitive(not app_installed)
            elif num_selected_uninstall > 0:
                app_checkbox.set_sensitive(app_installed)
            else:
                app_checkbox.set_sensitive(True)

    def action_selected_packages(self, widget):  # pylint: disable=unused-argument
        if not self.selected_packages:
            self.show_message("Action on Selected Packages", "No packages selected.")
            return

        self.action_button.hide()

        if self.selected_for_install:
            self.show_progress_bar("Installing...")
            self.run_install_uninstall(self.selected_for_install, "install", "Installing")
        elif self.selected_for_uninstall:
            self.show_progress_bar("Uninstalling...")
            self.run_install_uninstall(self.selected_for_uninstall, "remove", "Uninstalling")

    def run_install_uninstall(self, packages, action, action_text):
        def task():
            try:
                # Show "Preparing..." message
                GLib.idle_add(self.progress_bar.set_text, "Preparing...")
                time.sleep(2)

                # Step "pkexec asks for password" (no message)
                package_list = " ".join(packages)
                self.run_command(f"pkexec nala {action} -y {package_list}")

                # Show "Applying changes..." message
                GLib.idle_add(self.progress_bar.set_text, "Applying changes...")
                for i in range(1, 101):
                    GLib.idle_add(self.progress_bar.set_fraction, i / 100.0)
                    time.sleep(0.05)

                if action == "install":
                    GLib.idle_add(self.show_completion_dialog, "Installation Completed", "The packages have been installed successfully.")
                    GLib.idle_add(self.show_notification, "Installation Completed", "The packages have been installed successfully.")
                else:
                    GLib.idle_add(self.show_completion_dialog, "Uninstallation Completed", "The packages have been uninstalled successfully.")
                    GLib.idle_add(self.show_notification, "Uninstallation Completed", "The packages have been uninstalled successfully.")
            except subprocess.CalledProcessError:
                GLib.idle_add(self.show_message, "Error", f"Could not complete the action: {action_text.lower()}")
            finally:
                GLib.idle_add(self.hide_progress_bar)
                GLib.idle_add(self.action_button.show)
                GLib.idle_add(self.reset_selection)
                GLib.idle_add(self.update_app_status_multiple, packages)

        threading.Thread(target=task).start()

    def run_command(self, command):
        subprocess.run(command, shell=True, check=True)

    def cancel_installation(self, button):  # pylint: disable=unused-argument
        if self.activity:
            self._stop_event.set()
            self.show_message("Cancellation", "The installation/uninstallation has been canceled.")
            self.hide_progress_bar()
            self.action_button.show()
            self.reset_selection()

    def show_completion_dialog(self, title, message):
        dialog = Gtk.MessageDialog(parent=self, message_type=Gtk.MessageType.INFO, text=title, modal=True)
        dialog.format_secondary_text(message)
        dialog.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.show_all()

    def reset_selection(self):
        self.selected_packages = []
        self.selected_for_install = []
        self.selected_for_uninstall = []
        self.update_action_button()

    def update_app_status_multiple(self, commands):
        for command in commands:
            self.update_app_status(command)

    def update_app_status(self, command):
        app_box = self.app_boxes.get(command)
        if app_box:
            installed_label = app_box.get_children()[-1]
            if self.is_installed(command):
                installed_label.set_label("(Installed)")
            else:
                installed_label.set_label("")

    def update_all_app_statuses(self):
        for command in self.app_boxes:
            self.update_app_status(command)

    def show_message(self, title, message):
        dialog = Gtk.MessageDialog(parent=self, message_type=Gtk.MessageType.INFO, text=title, modal=True)
        dialog.format_secondary_text(message)
        dialog.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.show_all()

    def show_notification(self, title, message):
        notification = Notify.Notification.new(title, message)
        notification.show()

    def open_bauh(self, menuitem):  # pylint: disable=unused-argument
        subprocess.Popen(["bauh"], stderr=subprocess.PIPE)

    def show_about_dialog(self, widget):  # pylint: disable=unused-argument
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_program_name("CuerdOS Patchy")
        about_dialog.set_version("1.0 v040225 Elena")
        about_dialog.set_comments("Software Boutique for first use in CuerdOS GNU/Linux.")
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        current_dir = os.path.dirname(os.path.realpath(__file__))
        logo_path = os.path.join(current_dir, "/usr/share/patchy/patchy.svg")
        about_dialog.set_authors([
            "Ale D.M ",
            "Leo H. Pérez (GatoVerde95)",
            "Pablo G.",
            "Welkis",
            "GatoVerde95 Studios",
            "CuerdOS Community"
        ])
        about_dialog.set_copyright("© 2025 CuerdOS")

        if os.path.exists(logo_path):
            logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file(logo_path)
            about_dialog.set_logo(logo_pixbuf)
        about_dialog.run()
        about_dialog.destroy()

    def update_app_list(self, widget):  # pylint: disable=unused-argument
        self.show_message("Update Application List", "The application list has been updated.")
        # Here you can add logic to update the application list from an external source

    def search_app(self, search_entry):
        query = search_entry.get_text().lower()
        for page_num in range(self.notebook.get_n_pages()):
            category_box = self.notebook.get_nth_page(page_num)
            for child in category_box.get_children():
                app_label = child.get_children()[1]
                app_name = app_label.get_label().lower()
                if query in app_name:
                    self.notebook.set_current_page(page_num)
                    return
        self.show_message("Search Application", "No application found with that name.")

    def show_app_details(self, app):
        details_dialog = Gtk.Dialog(title=app["name"], parent=self, modal=True)
        details_dialog.set_default_size(400, 300)
        details_label = Gtk.Label(label=f"Name: {app['name']}\nDescription: {app['description']}\nCommand: {app['command']}")
        details_dialog.vbox.pack_start(details_label, True, True, 10)
        details_dialog.show_all()
        details_dialog.run()
        details_dialog.destroy()

if __name__ == "__main__":
    window = SoftwareBoutique()
    window.show_all()
    Gtk.main()