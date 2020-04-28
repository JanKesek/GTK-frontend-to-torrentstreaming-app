#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import os

def idle_add(old_func):
	def new_func(*args):
		GLib.idle_add(lambda: old_func(*args) and False)
	new_func.__name__ = old_func.__name__
	return new_func	
class Interface:
	def __init__(self, filename):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(filename)
		self.builder.connect_signals(self)
		self.window=self.builder.get_object("window1")
		self.button=self.builder.get_object("button1")
		self.box=self.builder.get_object("box1")
		self.entry=self.builder.get_object("entry1")
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
	def start_stop(self, *args):
		if self.button.get_label() == "Start":
			filepath = self.entry.get_text().strip()
			if os.path.isfile(filepath):
				filepath = os.path.realpath(filepath)
				self.button.set_label("Stop")
				#player.set_property("uri", "file://" + filepath)
				#player.set_state(Gst.State.PLAYING)
			else:
				#player.set_state(Gst.State.NULL)
				self.button.set_label("Start")
		else:
			print(self.button.get_label()=="Start")
			print("CANNOT START VIDEO, LABEL IS {}".format(self.button.get_label()))
if __name__ == '__main__':
	import sys, signal
	
	GLib.threads_init()
	
	mainloop = GLib.MainLoop()
	
	css = Gtk.CssProvider()
	css.load_from_path('style.css')
	Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER)


	

	interface = Interface()
	interface.window1.show_all()
	
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	sys.excepthook = lambda *args: (sys.__excepthook__(*args), mainloop.quit())
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()

