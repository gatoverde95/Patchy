#!/usr/bin/env python3
import gi
import subprocess
import threading
import time
import os

# Asegurarse de usar GTK 3
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GdkPixbuf

CATEGORIES = {
    "Internet": [
        {"name": "GNOME Epiphany", "command": "epiphany", "description": "Navegador web ligero de GNOME", "icon": "epiphany"},
        {"name": "Chromium", "command": "chromium", "description": "Navegador web", "icon": "chromium"},
        {"name": "uGet", "command": "uget", "description": "Descargador de archivos", "icon": "uget"},
        {"name": "Transmission", "command": "transmission-gtk", "description": "Cliente BitTorrent", "icon": "transmission"},
        {"name": "Telegram", "command": "telegram-desktop", "description": "Mensajería instantánea", "icon": "telegram"},
        {"name": "Evolution", "command": "evolution", "description": "Cliente de correo electrónico", "icon": "evolution"} 
    ],
    "Gráficos/Edición": [
        {"name": "GIMP", "command": "gimp", "description": "Editor de imágenes", "icon": "gimp"},
        {"name": "Inkscape", "command": "inkscape", "description": "Editor de gráficos vectoriales", "icon": "inkscape"},
        {"name": "darktable", "command": "darktable", "description": "Procesador de fotos en RAW", "icon": "darktable"},
        {"name": "Krita", "command": "krita", "description": "Herramienta de pintura digital", "icon": "krita"},
        {"name": "Eye of MATE", "command": "eom", "description": "Visor de imágenes", "icon": "eom"},
        {"name": "gThumb", "command": "gthumb", "description": "Visor y organizador de imágenes", "icon": "gthumb"}
    ],
    "Ofimática": [
        {"name": "LibreOffice", "command": "libreoffice", "description": "Suite ofimática", "icon": "libreoffice"},
        {"name": "Gnumeric", "command": "gnumeric", "description": "Hoja de cálculo", "icon": "gnucash-icon"},
        {"name": "Abiword", "command": "abiword", "description": "Procesador de texto", "icon": "abiword"},
        {"name": "Pluma", "command": "pluma", "description": "Editor de texto", "icon": "gedit"},
        {"name": "Galculate", "command": "galculate", "description": "Calculadora avanzada", "icon": "calc"}
    ],
    "Multimedia": [
        {"name": "VLC", "command": "vlc", "description": "Reproductor multimedia", "icon": "vlc"},
        {"name": "OBS", "command": "obs-studio", "description": "Software de streaming", "icon": "obs"},
        {"name": "Celluloid", "command": "celluloid", "description": "Reproductor de video", "icon": "celluloid"},
        {"name": "Audacity", "command": "audacity", "description": "Editor de audio", "icon": "audacity"},
        {"name": "Easyeffects", "command": "easyeffects", "description": "Efectos de audio", "icon": "easyeffects"},
        {"name": "Shotcut", "command": "shotcut", "description": "Editor de video", "icon": "photolayoutseditor"},
        {"name": "Audacious", "command": "audacious", "description": "Reproductor de música", "icon": "audacious"},
        {"name": "Cheese", "command": "cheese", "description": "Captura de fotos y videos", "icon": "cheese"},
        {"name": "VokoscreenNG", "command": "vokoscreen-ng", "description": "Software de grabación de pantalla", "icon": "screenrecorder"}
    ],
    "Sistema": [
        {"name": "Xfce Task Manager", "command": "xfce4-taskmanager", "description": "Administrador de tareas", "icon": "gnome-monitor"},
        {"name": "Kitty", "command": "kitty", "description": "Terminal moderna", "icon": "kitty"},
        {"name": "Tilix", "command": "tilix", "description": "Emulador de terminal", "icon": "tilix"},
        {"name": "Engrampa", "command": "engrampa", "description": "Gestor de archivos comprimidos", "icon": "engrampa"},
        {"name": "Q4Wine", "command": "q4wine", "description": "Compatibilidad de aplicaciones Windows", "icon": "q4wine"},
        {"name": "Wine", "command": "winecfg", "description": "Compatibilidad para ejecutar aplicaciones de Windows", "icon": "wine"},
        {"name": "Gdebi", "command": "gdebi", "description": "Instalador de paquetes .deb", "icon": "gdebi"},
        {"name": "File-Roller", "command": "file-roller", "description": "Gestor de archivos comprimidos", "icon": "file-roller"}
    ],
    "Desarrollo": [
        {"name": "Thonny", "command": "thonny", "description": "IDE para Python", "icon": "thonny"},
        {"name": "Geany", "command": "geany", "description": "Editor de texto para desarrollo", "icon": "geany"},
        {"name": "Bluefish", "command": "bluefish", "description": "Editor de texto para desarrollo web", "icon": "bluefish"},
        {"name": "KDevelop", "command": "kdevelop", "description": "IDE para desarrollo de software", "icon": "kdevelop"},
        {"name": "Emacs", "command": "emacs", "description": "Editor de texto extensible y personalizable", "icon": "emacs"}
    ]
}

class SoftwareBoutique(Gtk.Window):
    def __init__(self):
        super().__init__(title="CuerdOS Patchy")
        self.set_default_size(700, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(True)
        self.connect("destroy", Gtk.main_quit)

        current_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(current_dir, "log.svg")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)
        self.create_command_bar(main_box)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        main_box.pack_start(self.notebook, True, True, 0)

        for category, apps in CATEGORIES.items():
            tab_label = Gtk.Label(label=category)
            category_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
            for app in apps:
                app_box = self.create_app_box(app)
                category_box.pack_start(app_box, False, False, 0)
            self.notebook.append_page(category_box, tab_label)

    def create_command_bar(self, parent_box):
        menubar = Gtk.MenuBar()
        help_menu = Gtk.Menu()

        about_item = Gtk.MenuItem(label="Acerca de")
        about_item.connect("activate", self.show_about_dialog)
        help_menu.append(about_item)

        bauh_item = Gtk.MenuItem(label="Abrir Bauh")
        bauh_item.connect("activate", self.open_bauh)
        menubar.append(bauh_item)

        help_menu_item = Gtk.MenuItem(label="Ayuda")
        help_menu_item.set_submenu(help_menu)
        menubar.append(help_menu_item)
        parent_box.pack_start(menubar, False, False, 0)

    def create_app_box(self, app):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = Gtk.Image.new_from_icon_name(app["icon"], Gtk.IconSize.DIALOG)
        label = Gtk.Label(label=f"<b>{app['name']}</b>\n{app['description']}", use_markup=True)
        label.set_xalign(0)

        # Verificar si la aplicación ya está instalada
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
        """Verifica si el paquete está instalado."""
        try:
            subprocess.run(["which", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def on_install(self, button, app, install_button):
        """Maneja la instalación/desinstalación al hacer clic en el botón."""
        if button.get_label() == "Instalar":
            self.show_progress_bar(app["command"], app["name"], "Instalando...", install_button)
        else:
            self.show_progress_bar(app["command"], app["name"], "Desinstalando...", install_button)

    def show_progress_bar(self, command, package, action, install_button):
        dialog = Gtk.Dialog(title=action, parent=self, modal=True)
        dialog.set_default_size(400, 100)
        progress_bar = Gtk.ProgressBar()
        progress_bar.set_show_text(True)
        dialog.vbox.pack_start(progress_bar, True, True, 10)

        threading.Thread(target=self.run_install_uninstall, args=(command, package, action, progress_bar, dialog, install_button)).start()
        dialog.show_all()

    def run_install_uninstall(self, command, package, action, progress_bar, dialog, install_button):
        """Instala o desinstala un paquete mientras muestra una barra de progreso."""
        try:
            for i in range(1, 101):
                GLib.idle_add(progress_bar.set_fraction, i / 100.0)
                time.sleep(0.05)

            if action == "Instalando...":
                self.install_package(command, package)
                GLib.idle_add(install_button.set_label, "Desinstalar")
            else:
                self.run_command(f"pkexec nala remove -y {command}")
                GLib.idle_add(install_button.set_label, "Instalar")
        except subprocess.CalledProcessError:
            GLib.idle_add(self.show_message, "Error", f"No se pudo {action.lower()} {package}")
        finally:
            GLib.idle_add(dialog.destroy)

    def install_package(self, command, package):
        self.run_command(f"pkexec nala install -y {command}")

    def run_command(self, command):
        subprocess.run(command, shell=True, check=True)

    def show_message(self, title, message):
        dialog = Gtk.MessageDialog(parent=self, message_type=Gtk.MessageType.INFO, text=title, modal=True)
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def open_bauh(self, menuitem):
        subprocess.Popen(["bauh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def show_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_program_name("CuerdOS Patchy")
        about_dialog.set_version("1.0.1a v.171124b Elena")
        about_dialog.set_comments("Botique de Software para primer uso en CuerdOS GNU/Linux.")
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        current_dir = os.path.dirname(os.path.realpath(__file__))
        logo_path = os.path.join(current_dir, "logo.svg")
        about_dialog.set_authors([
    "Ale D.M ",
    "Leo H. Pérez (GatoVerde95)",
    "Pablo G.",
    "Welkis",
    "GatoVerde95 Studios",
    "CuerdOS Community",
    "Org. CuerdOS",
    "Stage 49"
])
        about_dialog.set_copyright("© 2024 CuerdOS")
        
        if os.path.exists(logo_path):
            logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file(logo_path)
            logo_pixbuf = logo_pixbuf.scale_simple(150, 150, GdkPixbuf.InterpType.BILINEAR)
            about_dialog.set_logo(logo_pixbuf)
        about_dialog.run()
        about_dialog.destroy()

if __name__ == "__main__":
    window = SoftwareBoutique()
    window.show_all()
    Gtk.main()
