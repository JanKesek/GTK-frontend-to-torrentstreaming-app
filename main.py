#!/usr/bin/python3

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')

from gi.repository import Gtk, GLib, Gdk, WebKit2

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
			self.builder.add_from_file('videoplayer2.glade')
			self.builder.connect_signals(self)
			
			self.webview = WebKit2.WebView()
			self.notebook1.append_page(self.webview)
			self.webview.show()
			self.notebook1.set_current_page(1)
			self.webview.load_uri('https://raw.githubusercontent.com/haael/white-box-fapkc/master/README.md')
			
			#self.drawingarea1.connect('draw', self.draw)
		
		def __getattr__(self, attr):
			widget = self.builder.get_object(attr)
			if widget == None:
				raise AttributeError("Widget not found: " + attr)
			return widget
		
		def draw(self, widget, ctx):
			ctx.set_source_rgb(0.7, 0.7, 1)
			ctx.paint()
		
		@idle_add
		def test(self, *args):
			print("test")
		
		@idle_add
		def quit(self, *args):
			mainloop.quit()
		
		@idle_add
		def mouse(self, widget, event):
			self.progressbar1.set_fraction(event.x / self.progressbar1.get_allocated_width())
			self.progresstext1.set_text(str(int(event.x)))
	
	interface = Interface()
	interface.window1.show_all()
	
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	sys.excepthook = lambda *args: (sys.__excepthook__(*args), mainloop.quit())
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()

