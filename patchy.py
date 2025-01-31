import gi
import subprocess
import threading
import time
import os
import json

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf

# Detectar si estamos en Wayland o X11
def detect_graphics_backend():
    session_type = os.getenv('XDG_SESSION_TYPE', '').lower()
    
    if session_type == 'wayland':
        print("Detectado Wayland")
    else:
        print("Detectado X11, usando backend X11")
        os.environ['GDK_BACKEND'] = 'x11'

detect_graphics_backend()

# Leer la lista de aplicaciones desde un archivo JSON
def load_applications(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

CATEGORIES = load_applications('/usr/share/patchy/apps/applications.json')

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

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)
        self.create_command_bar(main_box)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        main_box.pack_start(self.notebook, True, True, 0)

        self.populate_notebook()

    def create_command_bar(self, parent_box):
        menubar = Gtk.MenuBar()
        help_menu = Gtk.Menu()
        about_item = Gtk.MenuItem(label="Acerca de")
        about_item.connect("activate", self.show_about_dialog)
        help_menu.append(about_item)
        
        store_menu = Gtk.Menu()
        open_bauh_item = Gtk.MenuItem(label="Abrir Bauh")
        open_bauh_item.connect("activate", self.open_bauh)
        store_menu.append(open_bauh_item)
        
        update_item = Gtk.MenuItem(label="Actualizar Lista de Aplicaciones")
        update_item.connect("activate", self.update_app_list)
        store_menu.append(update_item)
        
        store_menu_item = Gtk.MenuItem(label="Tienda")
        store_menu_item.set_submenu(store_menu)
        menubar.append(store_menu_item)

        help_menu_item = Gtk.MenuItem(label="Ayuda")
        help_menu_item.set_submenu(help_menu)
        menubar.append(help_menu_item)
        parent_box.pack_start(menubar, False, False, 0)

    def populate_notebook(self):
        for category, apps in CATEGORIES.items():
            tab_label = Gtk.Label(label=category)
            category_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
            for app in apps:
                app_box = self.create_app_box(app)
                category_box.pack_start(app_box, False, False, 0)
            self.notebook.append_page(category_box, tab_label)

    def create_app_box(self, app):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Ruta a la carpeta de iconos locales
        current_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(current_dir, "/usr/share/patchy/icons", f"{app['icon']}.svg")
        
        if os.path.exists(icon_path):
            icon = Gtk.Image.new_from_file(icon_path)
        else:
            icon = Gtk.Image.new_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        
        label = Gtk.Label(label=f"<b>{app['name']}</b>\n{app['description']}", use_markup=True)
        label.set_xalign(0)

        if self.is_installed(app["command"]):
            button_label = "Desinstalar"
        else:
            button_label = "Instalar"
        
        install_button = Gtk.Button(label=button_label, margin=5)
        install_button.connect("clicked", self.on_install, app, install_button)
        box.pack_start(icon, False, False, 0)
        box.pack_start(label, True, True, 0)
        box.pack_end(install_button, False, False, 0)
        return box

    def is_installed(self, command):
        try:
            subprocess.run(["which", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def on_install(self, button, app, install_button):
        if button.get_label() == "Instalar":
            self.show_progress_bar(app["command"], app["name"], "Espere un momento se esta Instalando...", install_button)
        else:
            self.show_progress_bar(app["command"], app["name"], "Espere un momento se esta Desinstalando...", install_button)

    def show_progress_bar(self, command, package, action, install_button):
        dialog = Gtk.Dialog(title=action, parent=self, modal=True)
        dialog.set_default_size(400, 100)
        progress_bar = Gtk.ProgressBar()
        progress_bar.set_show_text(True)
        dialog.vbox.pack_start(progress_bar, True, True, 10)

        threading.Thread(target=self.run_install_uninstall, args=(command, package, action, progress_bar, dialog, install_button)).start()
        dialog.show_all()

    def run_install_uninstall(self, command, package, action, progress_bar, dialog, install_button):
        try:
            for i in range(1, 101):
                GLib.idle_add(progress_bar.set_fraction, i / 100.0)
                time.sleep(0.05)

            if action == "Espere un momento se esta Instalando...":
                self.install_package(command)
                GLib.idle_add(install_button.set_label, "Desinstalar")
                GLib.idle_add(self.show_message, "Instalación completada", f"{package} se ha instalado correctamente.")
            else:
                self.run_command(f"pkexec nala remove -y {command}")
                GLib.idle_add(install_button.set_label, "Instalar")
                GLib.idle_add(self.show_message, "Desinstalación completada", f"{package} se ha desinstalado correctamente.")
        except subprocess.CalledProcessError:
            GLib.idle_add(self.show_message, "Error", f"No se pudo {action.lower()} {package}")
        finally:
            GLib.idle_add(dialog.destroy)

    def install_package(self, command):
        self.run_command(f"pkexec nala install -y {command}")

    def run_command(self, command):
        subprocess.run(command, shell=True, check=True)

    def show_message(self, title, message):
        dialog = Gtk.MessageDialog(parent=self, message_type=Gtk.MessageType.INFO, text=title, modal=True)
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def open_bauh(self, menuitem):
        # pylint: disable=unused-argument
        subprocess.Popen(["bauh"], stderr=subprocess.PIPE)

    def show_about_dialog(self, widget):
        # pylint: disable=unused-argument
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_program_name("CuerdOS Patchy")
        about_dialog.set_version("1.0 v100125 Elena")
        about_dialog.set_comments("Botique de Software para primer uso en CuerdOS GNU/Linux.")
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

    def update_app_list(self, widget):
        # pylint: disable=unused-argument
        self.show_message("Actualizar Lista de Aplicaciones", "La lista de aplicaciones se ha actualizado.")
        # Aquí puedes agregar lógica para actualizar la lista de aplicaciones desde un origen externo

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
        self.show_message("Buscar Aplicación", "No se encontró ninguna aplicación con ese nombre.")
    
    def show_app_details(self, app):
        details_dialog = Gtk.Dialog(title=app["name"], parent=self, modal=True)
        details_dialog.set_default_size(400, 300)
        details_label = Gtk.Label(label=f"Nombre: {app['name']}\nDescripción: {app['description']}\nComando: {app['command']}")
        details_dialog.vbox.pack_start(details_label, True, True, 10)
        details_dialog.show_all()
        details_dialog.run()
        details_dialog.destroy()

if __name__ == "__main__":
    window = SoftwareBoutique()
    window.show_all()
    Gtk.main()
