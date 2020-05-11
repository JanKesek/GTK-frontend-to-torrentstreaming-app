#!/usr/bin/python3


import os, gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gtk, GLib, Gdk, Gst, WebKit2
from gi.repository import GdkX11, GstVideo


def idle_add(old_func):
	def new_func(*args):
		GLib.idle_add(old_func, *args)
	new_func.__name__ = old_func.__name__
	return new_func


class Interface:
	def __init__(self, mainloop):
		self.mainloop = mainloop
		
		self.builder = Gtk.Builder()
		self.builder.add_from_file('videoplayer3.glade')
		self.builder.connect_signals(self)
		
		self.movie_window.connect('draw', self.movie_window_background)
		
		self.webview = WebKit2.WebView()
		self.webview.set_margin_top(60)
		self.webview.set_margin_bottom(60)
		self.notebook1.append_page(self.webview)
		self.webview.show()
		self.webview.load_uri('https://raw.githubusercontent.com/haael/white-box-fapkc/master/README.md')

		self.player = Gst.ElementFactory.make("playbin", "player")
		bus = self.player.get_bus()
		bus.add_signal_watch()
		bus.enable_sync_message_emission()
		bus.connect("message", self.on_message)
		bus.connect("sync-message::element", self.on_sync_message)
		
		self.progressbar.set_fraction(0)
		self.change_volume()
		GLib.timeout_add(1000, self.elapsing_progress)

	def __getattr__(self, attr):
		widget = self.builder.get_object(attr)
		if widget == None:
			raise AttributeError("Widget not found: " + attr)
		return widget
	
	def movie_window_background(self, widget, ctx):
		ctx.set_source_rgb(0, 0, 0)
		ctx.paint()
	
	@idle_add
	def quit(self, *args):
		print("quit")
		idle_add(lambda: self.player.set_state(Gst.State.NULL))()
		self.mainloop.quit()
	
	@idle_add
	def open_url(self, *args):
		print("current working directory", os.getcwd())
		filepath = os.getcwd() + "/" + self.entry1.get_text().strip()
		if os.path.isfile(filepath):
			filepath = os.path.realpath(filepath)
			self.player.set_property("uri", "file://" + filepath)
		else:
			self.player.set_state(Gst.State.NULL)
	
	@idle_add
	def play(self, *args):
		self.player.set_state(Gst.State.PLAYING)
		self.change_volume()
		self.notebook1.set_current_page(0)
		self.elapsing_progress()
	
	@idle_add
	def pause(self, *args):
		self.player.set_state(Gst.State.PAUSED)
		self.elapsing_progress()
		self.notebook1.set_current_page(0)
	
	@idle_add
	def stop(self, *args):
		self.player.set_state(Gst.State.NULL)
		self.notebook1.set_current_page(1)
		self.progressbar.set_fraction(0)
		self.progresstext.set_text("")
	
	@idle_add
	def change_volume(self, *args):
		new_volume = self.volumebutton1.get_value()
		self.player.set_property('volume', new_volume)

	@idle_add
	def rewind(self, *args):
		current = self.player.query_position(Gst.Format.TIME)[1] / Gst.SECOND
		self.seek(current - 5)
	
	@idle_add
	def forward(self, *args):
		current = self.player.query_position(Gst.Format.TIME)[1] / Gst.SECOND
		self.seek(current + 5)
	
	def seek(self, position):
		print("seek to:", position)
		self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, Gst.SECOND * position)
	
	#def elapsing_progress(self):
	#	self.t=threading.Timer(1.0,self.elapsing_progress)
	#	self.t.daemon=True
	#	self.t.start()
	#	curr=self.progressbar.get_fraction()
	#	if self.duration==0.0:
	#		self.duration=self.player.query_duration(Gst.Format.TIME)[1]/Gst.SECOND
	#		self.progressbar.set_fraction(curr+0.01)
	#	else:
	#		self.progressbar.set_fraction(curr+(1.0/self.duration))
	#	if curr==1.0:
	#		self.finished=True
	#		self.t.cancel()
	#	#print("OBECNY CZAS FILMU: ", curr)

	#def resume(self):
	#	self.t=threading.Timer(1.0, self.elapsing_progress)
	#	self.t.daemon=True
	#	self.t.start()
	
	def elapsing_progress(self):
		if self.player.current_state not in [Gst.State.PLAYING, Gst.State.PAUSED]: return True
		current = self.player.query_position(Gst.Format.TIME)[1] / Gst.SECOND
		duration = self.player.query_duration(Gst.Format.TIME)[1] / Gst.SECOND
		print("position:", current, duration, current / duration)
		self.progressbar.set_fraction(current / duration)
		self.progresstext.set_text(str(current) + " / " + str(duration))
		return True
	
	@idle_add
	def progress_mouse(self, widget, event):
		x = float(event.x)
		seek_perc = x / self.progressbar.get_allocated_width()
		self.progressbar.set_fraction(seek_perc)
		duration = self.player.query_duration(Gst.Format.TIME)[1] / Gst.SECOND
		self.progresstext.set_text(str(duration * seek_perc) + " / " + str(duration))
		
		print("progressbar:", x, self.progressbar.get_allocated_width(), seek_perc, duration, duration * seek_perc)
		
		self.seek(duration * seek_perc)
	
	def on_message(self, bus, message):
		t = message.type
		if t == Gst.MessageType.EOS:
			self.player.set_state(Gst.State.NULL)
			idle_add(lambda: self.progressbar.set_fraction(1.0))()
		elif t == Gst.MessageType.ERROR:
			self.player.set_state(Gst.State.NULL)
			err, debug = message.parse_error()
			print("Error: {}".format(err, debug))
	
	@idle_add
	def on_sync_message(self, bus, message):
		if message.get_structure().get_name() == 'prepare-window-handle':
			imagesink = message.src
			imagesink.set_property("force-aspect-ratio", True)
			print("xid", self.movie_window.get_property('window').get_xid())
			imagesink.set_window_handle(self.movie_window.get_property('window').get_xid())


if __name__ == '__main__':
	import sys, signal
	
	GLib.threads_init()
	Gst.init(None)
	
	mainloop = GLib.MainLoop()
	
	css = Gtk.CssProvider()
	css.load_from_path('style.css')
	Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER)
	
	interface = Interface(mainloop)
	interface.main_window.show_all()
	interface.notebook1.set_current_page(1) # 0 - player, 1 - webview
	
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	sys.excepthook = lambda *args: (sys.__excepthook__(*args), mainloop.quit())
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()

