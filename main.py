#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

if __name__ == '__main__':
	import sys, signal
	
	GLib.threads_init()
	
	mainloop = GLib.MainLoop()
	
	css = Gtk.CssProvider()
	css.load_from_path('style.css')
	Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER)

	def idle_add(old_func):
		def new_func(*args):
			GLib.idle_add(lambda: old_func(*args) and False)
		new_func.__name__ = old_func.__name__
		return new_func
	
	class Interface:
		def __init__(self):
			self.builder = Gtk.Builder()
			self.builder.add_from_file('interface.glade')
			self.builder.connect_signals(self)
		
		def __getattr__(self, attr):
			widget = self.builder.get_object(attr)
			if widget == None:
				raise AttributeError("Widget not found: " + attr)
			return widget
		
		@idle_add
		def test(self, *args):
			print("test")
		
		@idle_add
		def quit(self, *args):
			mainloop.quit()
	
	interface = Interface()
	interface.window1.show_all()
	
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	sys.excepthook = lambda *args: (sys.__excepthook__(*args), mainloop.quit())
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()

