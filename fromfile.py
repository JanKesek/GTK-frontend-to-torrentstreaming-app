import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

#window = Gtk.Window(title="Hello World")
builder=Gtk.Builder()
builder.add_from_file("videoplayer2.glade")
window=builder.get_object("window1")
window.show_all()
window.connect("destroy", Gtk.main_quit)
Gtk.main()
