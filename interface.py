#!/usr/bin/python3
#-*- coding: utf-8 -*-

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>


"User interface for MediaKilla."


__author__ = "Janjk"
__credits__ = ["haael <jid:haael@jabber.at>", "Janjk <jid:jklambda@jabber.hot-chilli.net>"]

__copyright__ = "haael.co.uk/prim LTD"
__license__ = 'GPLv3+'

__version__ = '0.0'
__status__ = 'alpha'


__all__ = 'Interface',


import logging

log = logging.getLogger('interface')
log.setLevel(logging.DEBUG)
if __debug__:
	log.addHandler(logging.StreamHandler())

import gi

gi.require_version('Gtk', '3.0')

from gi.repository import GObject, Gtk, Gdk, GdkX11, GLib

from utils import *


class Interface(GObject.Object):
	__gsignals__ = {
		'open-url':			(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_STRING,)),
		'play':				(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
		'pause':			(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
		'rewind':			(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_FLOAT,)),
		'forward':			(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_FLOAT,)),
		'stop':				(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
		'seek':				(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_FLOAT,)),
		'change-volume':	(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_FLOAT,)),
		'quit':				(GObject.SIGNAL_RUN_LAST,  GObject.TYPE_NONE, ())
	}
	
	def __init__(self, glade_path):
		log.info("Creating interface.")
		log.debug("Interface.__init__('%s')", glade_path)
		
		super().__init__()
		
		self.builder = Gtk.Builder()
		self.builder.add_from_file(glade_path)
		self.builder.connect_signals(self)
		
		self.main_window.connect('window-state-event', self.window_state_event)
		
		self.progressbar.set_fraction(0)
		self.progresstext.set_text("")
		
		self.duration = 0
		self.is_fullscreen = False
		self.last_player_state = PlayerState.UNKNOWN
		self.suppress_pause_toggle = False
		self.suppress_fullscreen_toggle = False
	
	def __getattr__(self, attr):
		widget = self.builder.get_object(attr)
		if widget == None:
			raise AttributeError("Widget not found: " + attr)
		return widget
	
	@idle_add
	def quit(self, *args):
		log.debug('quit')
		self.emit('stop')
		self.emit('quit')
	
	def window_state_event(self, mainwindow, event):
		new_fullscreen = bool(event.new_window_state & Gdk.WindowState.FULLSCREEN)
		if self.is_fullscreen != new_fullscreen:
			if new_fullscreen:
				log.info("fullscreen")
			else:
				log.info("unfullscreen")
			self.is_fullscreen = new_fullscreen
			self.update_interface_visibility()
			if new_fullscreen != self.fullscreen_button.get_active():
				self.suppress_fullscreen_toggle = True
				self.fullscreen_button.set_active(new_fullscreen)
	
	@idle_add
	def show_elements(self, *args):
		if self.is_fullscreen and not self.progress_box.is_visible():
			self.movie_window.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.ARROW))
			self.address_box.set_visible(False)
			self.progress_box.set_visible(True)
			self.button_box.set_visible(True)
			GLib.timeout_add(5000, (lambda: self.update_interface_visibility() and False))
	
	@idle_add
	def fullscreen(self, *args):
		if self.last_player_state == PlayerState.PLAYING:
			self.movie_window.grab_focus()
		elif self.last_player_state == PlayerState.PAUSED:
			self.pausebutton.grab_focus()
		
		if self.suppress_fullscreen_toggle:
			self.suppress_fullscreen_toggle = False
			return
		
		if self.fullscreen_button.get_active():
			log.debug("Fullscreen button pressed.")
			self.main_window.fullscreen()
		else:
			log.debug("Fullscreen button unpressed.")
			self.main_window.unfullscreen()
	
	@idle_add
	def update_interface_visibility(self):
		if self.last_player_state in [PlayerState.PLAYING, PlayerState.PAUSED]:
			self.show_player_tab()
		else:
			self.show_webview_tab()
		
		movie_gdk_window = self.movie_window.get_window()
		
		if not self.is_fullscreen:
			if movie_gdk_window: movie_gdk_window.set_cursor(Gdk.Cursor(Gdk.CursorType.ARROW))
			self.address_box.set_visible(True)
			self.progress_box.set_visible(True)
			self.button_box.set_visible(True)
		elif self.last_player_state == PlayerState.PLAYING:
			if movie_gdk_window: movie_gdk_window.set_cursor(Gdk.Cursor(Gdk.CursorType.BLANK_CURSOR))
			self.address_box.set_visible(False)
			self.progress_box.set_visible(False)
			self.button_box.set_visible(False)
		elif self.last_player_state == PlayerState.PAUSED:
			if movie_gdk_window: movie_gdk_window.set_cursor(Gdk.Cursor(Gdk.CursorType.ARROW))
			self.address_box.set_visible(False)
			self.progress_box.set_visible(True)
			self.button_box.set_visible(True)
		else:
			if movie_gdk_window: movie_gdk_window.set_cursor(Gdk.Cursor(Gdk.CursorType.ARROW))
			self.address_box.set_visible(True)
			self.progress_box.set_visible(True)
			self.button_box.set_visible(True)
		
		if self.last_player_state == PlayerState.PAUSED and not self.pausebutton.get_active():
			self.suppress_pause_toggle = True
			self.pausebutton.set_active(True)
		elif self.last_player_state != PlayerState.PAUSED and self.pausebutton.get_active():
			self.suppress_pause_toggle = True
			self.pausebutton.set_active(False)
	
	@idle_add
	def open_url(self, *args):
		uri = self.entry1.get_text().strip()
		self.emit('open-url', uri)
		self.pausebutton.grab_focus()
	
	@idle_add
	def play(self, *args):
		self.movie_window.grab_focus()
		if self.pausebutton.get_active():
			self.suppress_pause_toggle = True
			self.pausebutton.set_active(False)
		self.change_volume()
		self.emit('play')
	
	@idle_add
	def pause(self, *args):
		if not self.pausebutton.get_active():
			self.suppress_pause_toggle = True
			self.pausebutton.set_active(True)
		self.emit('pause')
	
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
		
		self.emit('stop')
		self.progressbar.set_fraction(0)
		self.progresstext.set_text("")
		self.last_player_state = PlayerState.UNKNOWN
		self.update_interface_visibility()
	
	@idle_add
	def change_volume(self, *args):
		new_volume = self.volumebutton1.get_value()
		self.emit('change-volume', new_volume)
	
	@idle_add
	def rewind(self, *args):
		self.emit('rewind', 5)
	
	@idle_add
	def forward(self, *args):
		self.emit('forward', 5)
	
	def seek(self, position):
		self.emit('seek', position)
	
	@idle_add
	def current_position(self, position, duration):
		self.duration = duration
		if duration > 0.00001:
			self.progressbar.set_fraction(position / duration)
			self.progresstext.set_text(str(int(position)) + " / " + str(int(duration)))
		else:
			self.progressbar.set_fraction(0)
			self.progresstext.set_text("")
	
	@idle_add
	def progress_mouse(self, widget, event):
		x = float(event.x)
		try:
			seek_perc = x / self.progressbar.get_allocated_width()
		except ZeroDivisionError:
			return
		self.progressbar.set_fraction(seek_perc)
		duration = self.duration
		self.progresstext.set_text(str(int(duration * seek_perc)) + " / " + str(int(duration)))
		
		log.debug("progressbar: x=%f width=%f percentage=%f duration=%f position=%f", x, self.progressbar.get_allocated_width(), seek_perc, duration, duration * seek_perc)
		
		self.seek(duration * seek_perc)
	
	def player_state_changed(self, new_state):
		if self.last_player_state != new_state:
			print(self.last_player_state)
			self.last_player_state = PlayerState(new_state)
			self.update_interface_visibility()
	
	def get_window_xid(self):
		return self.movie_window.get_property('window').get_xid()
	
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
			log.debug("movie_window_keydown %d", event.keyval)
		return False
	
	def movie_window_keyup(self, widget, event):
		return event.keyval in [32]
	
	def show_player_tab(self):
		self.notebook1.set_current_page(0)
	
	def show_webview_tab(self):
		self.notebook1.set_current_page(1)

GObject.type_register(Interface)


if __name__ == '__main__':
	from pathlib import Path
	from utils import idle_add, enable_exceptions, report_exceptions
	import time
	
	log_file = Path('/tmp/mediakilla-interface.log')
	logging.basicConfig(filename=str(log_file), filemode='w')
	log.info("Start: %s", time.strftime('%Y-%m-%d %H:%M:%S'))
	
	GLib.threads_init()
	
	path = Path('')
	
	css = Gtk.CssProvider()
	if Gtk.get_major_version() >= 3 and Gtk.get_minor_version() >= 22:
		css.load_from_path(str(path / 'style-3.22.css'))
	else:
		css.load_from_path(str(path / 'style-3.18.css'))
	Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER)
	
	interface = Interface(str(path / 'videoplayer.glade'))
	interface.main_window.show_all()
	
	interface.connect('open-url', lambda iface, url: log.info("open-url %s", url))
	interface.connect('play', lambda iface: log.info("play"))
	interface.connect('pause', lambda iface: log.info("pause"))
	interface.connect('rewind', lambda iface, seconds: log.info("rewind %f", seconds))
	interface.connect('forward', lambda iface, seconds: log.info("forward %f", seconds))
	interface.connect('stop', lambda iface: log.info("stop"))
	interface.connect('seek', lambda iface, position: log.info("seek %f", position))
	interface.connect('change-volume', lambda iface, volume: log.info("change-volume %f", volume))
	interface.connect('quit', lambda iface: Gtk.main_quit())
	
	idle_add(enable_exceptions)(log)
	
	try:
		Gtk.main()
	except KeyboardInterrupt:
		print()
	
	log.info("Stop: %s", time.strftime('%Y-%m-%d %H:%M:%S'))
	
	report_exceptions(log, log_file)



