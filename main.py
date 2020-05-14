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
		
		#self.movie_window.connect('draw', self.movie_window_background)
		self.main_window.connect('window-state-event', self.window_state_event)
		
		self.webview = WebKit2.WebView()
		self.webview.set_margin_top(60)
		self.webview.set_margin_bottom(60)
		self.notebook1.append_page(self.webview)
		self.webview.show()
		self.webview.load_uri('https://kukai.app/')

		self.player = Gst.ElementFactory.make("playbin", "player")
		bus = self.player.get_bus()
		bus.add_signal_watch()
		bus.enable_sync_message_emission()
		bus.connect("message", self.on_message)
		bus.connect("sync-message::element", self.on_sync_message)
		
		self.progressbar.set_fraction(0)
		self.change_volume()
		GLib.timeout_add(1000, self.elapsing_progress)
		
		self.is_fullscreen = False
		self.last_player_state = None
		self.suppress_pause_toggle = False
		self.suppress_fullscreen_toggle = False
	
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
		GLib.idle_add(self.player.set_state, Gst.State.NULL)
		self.mainloop.quit()
	
	def window_state_event(self, mainwindow, event):
		new_fullscreen = bool(event.new_window_state & Gdk.WindowState.FULLSCREEN)
		if self.is_fullscreen != new_fullscreen:
			self.is_fullscreen = new_fullscreen
			self.update_interface_visibility()
	
	@idle_add
	def show_elements(self,*args):
		#print(self.progress_box.is_visible())
		if not self.progress_box.is_visible():
			self.progress_box.set_visible(True)
			self.box4.set_visible(True)
			self.box5.set_visible(True)			
			GLib.timeout_add(5000, self.hide_elements)
	def hide_elements(self,*args):
		print(self.progress_box.is_visible(), " ", self.box4.is_visible())
		if self.progress_box.is_visible():
			self.progress_box.set_visible(False)
		#self.main_window.set_decorated(False)
			self.box5.set_visible(False)
			self.box4.set_visible(False)
		return False


	@idle_add
	def fullscreen(self,*args):
		if self.player.target_state == Gst.State.PLAYING:
			self.movie_window.grab_focus()
		elif self.player.target_state == Gst.State.PAUSED:
			self.pausebutton.grab_focus()
		
		if self.suppress_fullscreen_toggle:
			self.suppress_fullscreen_toggle = False
			return
		
		if self.fullscreen_button.get_active():
			print("fullscreen")
			self.main_window.fullscreen()
		else:
			print("unfullscreen")
			self.main_window.unfullscreen()
	
	@idle_add
	def update_interface_visibility(self):
		if self.player.target_state in [Gst.State.PLAYING, Gst.State.PAUSED]:
			self.notebook1.set_current_page(0)
		else:
			self.notebook1.set_current_page(1)
		
		if not self.is_fullscreen:
			self.address_box.set_visible(True)
			self.progress_box.set_visible(True)
			self.button_box.set_visible(True)
		elif self.player.target_state == Gst.State.PLAYING:
			self.address_box.set_visible(False)
			self.progress_box.set_visible(False)
			self.button_box.set_visible(False)
		elif self.player.target_state == Gst.State.PAUSED:
			self.address_box.set_visible(False)
			self.progress_box.set_visible(True)
			self.button_box.set_visible(True)
		else:
			self.address_box.set_visible(True)
			self.progress_box.set_visible(True)
			self.button_box.set_visible(True)

	@idle_add
	def open_url(self, *args):
		print("current working directory", os.getcwd())
		filepath = os.getcwd() + "/" + self.entry1.get_text().strip()
		self.hide_elements()
		if os.path.isfile(filepath):
			filepath = os.path.realpath(filepath)
			self.player.set_property("uri", "file://" + filepath)
			self.pause()
			self.pausebutton.grab_focus()
			GLib.timeout_add(500, self.seek, 0)
		else:
			self.stop()
	
	@idle_add
	def play(self, *args):
		self.movie_window.grab_focus()
		if self.pausebutton.get_active():
			self.suppress_pause_toggle = True
			self.pausebutton.set_active(False)
		self.player.set_state(Gst.State.PLAYING)
		self.elapsing_progress()
	
	@idle_add
	def pause(self, *args):
		if not self.pausebutton.get_active():
			self.suppress_pause_toggle = True
			self.pausebutton.set_active(True)
		self.player.set_state(Gst.State.PAUSED)
		self.elapsing_progress()
	
	@idle_add
	def toggle(self, *args):
		if self.suppress_pause_toggle:
			self.suppress_pause_toggle = False
			return
		
		if self.pausebutton.get_active():
			self.pause()
		else:
			self.play()
	
	@idle_add
	def stop(self, *args):
		if self.pausebutton.get_active():
			self.suppress_pause_toggle = True
			self.pausebutton.set_active(False)
		
		self.player.set_state(Gst.State.NULL)
		self.progressbar.set_fraction(0)
		self.progresstext.set_text("")
		self.last_player_state = None
		self.update_interface_visibility()
	
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
		
	def elapsing_progress(self):
		if self.player.target_state not in [Gst.State.PLAYING, Gst.State.PAUSED]: return True
		current = self.player.query_position(Gst.Format.TIME)[1] / Gst.SECOND
		duration = self.player.query_duration(Gst.Format.TIME)[1] / Gst.SECOND
		#print("position:", current, duration, current / duration)
		if duration > 0.00001:
			self.progressbar.set_fraction(current / duration)
			self.progresstext.set_text(str(current) + " / " + str(duration))
		else:
			self.progressbar.set_fraction(0)
			self.progresstext.set_text("")
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
	
	@idle_add
	def on_message(self, bus, message):
		t = message.type
		if t == Gst.MessageType.EOS:
			GLib.idle_add(self.progressbar.set_fraction, 1.0)
			self.pause()
		elif t == Gst.MessageType.ERROR:
			err, debug = message.parse_error()
			print("Error:", err, debug)
			self.stop()
		elif t == Gst.MessageType.STATE_CHANGED:
			if self.last_player_state != self.player.target_state:
				#print(self.player.target_state)
				self.last_player_state = self.player.target_state
				self.update_interface_visibility()
	
	@idle_add
	def on_sync_message(self, bus, message):
		if message.get_structure().get_name() == 'prepare-window-handle':
			imagesink = message.src
			imagesink.set_property("force-aspect-ratio", True)
			xid = self.movie_window.get_property('window').get_xid()
			print("xid", xid)
			imagesink.set_window_handle(xid)
	
	def main_window_keydown(self, widget, event):
		if event.keyval == 65307: # escape
			self.main_window.unfullscreen()
			self.suppress_fullscreen_toggle = True
			if self.fullscreen_button.get_active():
				self.fullscreen_button.set_active(False)
			return True
		elif event.keyval == 65480: # F11
			if not self.is_fullscreen:
				self.main_window.fullscreen()
				self.suppress_fullscreen_toggle = True
				if not self.fullscreen_button.get_active():
					self.fullscreen_button.set_active(True)
			else:
				self.main_window.unfullscreen()
				self.suppress_fullscreen_toggle = True
				if self.fullscreen_button.get_active():
					self.fullscreen_button.set_active(False)
			return True
		return False
	
	def main_window_keyup(self, widget, event):
		return event.keyval in [65307, 65480]
	
	def movie_window_keydown(self, widget, event):
		if event.keyval == 32: # space
			self.pause()
			self.pausebutton.grab_focus()
			return True
		else:
			print("movie_window_keydown", event.keyval)
		return False
	
	def movie_window_keyup(self, widget, event):
		return event.keyval in [32]


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

