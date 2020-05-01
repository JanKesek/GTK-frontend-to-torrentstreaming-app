#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Gst
import os, time
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
			Gst.init(None)
			self.player = Gst.ElementFactory.make("playbin", "player")
			self.movie_window=self.builder.get_object("drawingarea1")
			bus = self.player.get_bus()
			bus.add_signal_watch()
			bus.connect("message", self.on_message)
			bus.connect("sync-message::element",self.on_sync_message)
			
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
						print("quit")
						mainloop.quit()
		@idle_add
		def open_url(self, *args):
			print("current working directory", os.getcwd())
			filepath = os.getcwd()+"/"+self.entry1.get_text().strip()
			if os.path.isfile(filepath):
				filepath = os.path.realpath(filepath)
				self.player.set_property("uri", "file://" + filepath)
				self.player.set_state(Gst.State.PLAYING)
			else:
				self.player.set_state(Gst.State.NULL)
		def on_message(self, bus, message):
			t = message.type
			if t == Gst.MessageType.EOS:
				self.player.set_state(Gst.State.NULL)
			elif t == Gst.MessageType.ERROR:
				self.player.set_state(Gst.State.NULL)
				err, debug = message.parse_error()
				print("Error: {}".format(err, debug))
		def on_sync_message(self, bus, message):
			if message.get_structure().get_name() == 'prepare-window-handle':
				imagesink = message.src
				imagesink.set_property("force-aspect-ratio", True)
				imagesink.set_window_handle(self.movie_window.get_property('window').get_xid())


	interface = Interface()
	interface.window1.show_all()
	
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	sys.excepthook = lambda *args: (sys.__excepthook__(*args), mainloop.quit())
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()

