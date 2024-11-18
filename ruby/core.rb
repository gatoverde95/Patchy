require 'gtk3'
require 'json'
require 'fileutils'

# Asegúrate de usar la versión correcta de GTK
Gtk.init

# Definición de las categorías y aplicaciones
CATEGORIES = {
  "Audio" => [
    { "name" => "VLC", "description" => "Reproductor de medios", "installed" => false },
    { "name" => "Audacity", "description" => "Editor de audio", "installed" => false }
  ],
  "Video" => [
    { "name" => "OBS", "description" => "Software de grabación y transmisión en vivo", "installed" => false }
  ]
}

class SoftwareBoutique < Gtk::Window
  def initialize
    super
    set_title("CuerdOS Patchy")
    set_default_size(700, 500)

    set_position(Gtk::WindowPosition::CENTER)
    signal_connect("destroy") { Gtk.main_quit }

    current_dir = File.dirname(File.realpath(__FILE__))
    icon_path = File.join(current_dir, "log.svg")
    set_icon_from_file(icon_path) if File.exist?(icon_path)

    main_box = Gtk::Box.new(:vertical)
    add(main_box)
    create_command_bar(main_box)

    @notebook = Gtk::Notebook.new
    @notebook.set_scrollable(true)
    main_box.pack_start(@notebook, true, true, 0)

    # Añadir categorías y aplicaciones
    CATEGORIES.each do |category, apps|
      tab_label = Gtk::Label.new(category)
      category_box = Gtk::Box.new(:vertical, 10)
      apps.each do |app|
        app_box = create_app_box(app)
        category_box.pack_start(app_box, false, false, 0)
      end
      @notebook.append_page(category_box, tab_label)
    end
  end

  def create_command_bar(parent_box)
    # Aquí agregarías los comandos adicionales de la barra de comandos
    # Puedes usar una barra de herramientas con botones si es necesario
  end

  def create_app_box(app)
    app_box = Gtk::Box.new(:horizontal, 10)
    name_label = Gtk::Label.new(app["name"])
    description_label = Gtk::Label.new(app["description"])
    install_button = Gtk::Button.new(label: app["installed"] ? "Desinstalar" : "Instalar")
    install_button.signal_connect("clicked") { toggle_install(install_button, app) }
    
    app_box.pack_start(name_label, true, true, 0)
    app_box.pack_start(description_label, true, true, 0)
    app_box.pack_start(install_button, false, false, 0)

    app_box
  end

  def toggle_install(button, app)
    # Cambia el estado de la instalación
    app["installed"] = !app["installed"]
    button.label = app["installed"] ? "Desinstalar" : "Instalar"
  end
end

# Crear y mostrar la ventana
window = SoftwareBoutique.new
window.show_all
Gtk.main

