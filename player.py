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


"Player view for MediaKilla."


__author__ = "Janjk"
__credits__ = ["haael <jid:haael@jabber.at>", "Janjk <jid:jklambda@jabber.hot-chilli.net>"]

__copyright__ = "haael.co.uk/prim LTD"
__license__ = 'GPLv3+'

__version__ = '0.0'
__status__ = 'alpha'


__all__ = 'Player',


import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import GObject, GLib, Gst, GstVideo

from utils import *


if __name__ == '__main__':
	GLib.threads_init()
	Gst.init(None)
elif not Gst.is_initialized():
	raise ImportError("GStreamer must be initialized with `Gst.init(sys.argv)` before you attempt to import this library.")


class Player(GObject.Object):
	__gsignals__ = {
		'xid-needed':		(GObject.SIGNAL_RUN_LAST, GObject.TYPE_INT,  ()),
		'current-position':	(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_INT, GObject.TYPE_INT)),
		'state-changed':	(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_INT,)),
		'eos':				(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
		'error':			(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_STRING, GObject.TYPE_STRING))
	}
	
	def __init__(self):
		super().__init__()
		
		self.last_player_state = PlayerState.UNKNOWN
		
		self.player = Gst.ElementFactory.make("playbin", "player")
		
		self.bus = self.player.get_bus()
		self.bus.add_signal_watch()
		self.bus.enable_sync_message_emission()
		
		conn1 = self.bus.connect('message', self.on_message)
		conn2 = self.bus.connect('sync-message::element', self.on_sync_message)
		
		self.connections = frozenset([conn1, conn2])
		self.position_sending = GLib.timeout_add(1000, (lambda: self.emit_current_position() or True))
	
	def __del__(self):
		GLib.source_remove(self.position_sending)
		for conn in self.connections:
			self.disconnect(conn)
	
	def open_url(self, uri):
		from pathlib import Path
		
		self.stop()
		
		filepath = Path(uri)
		if filepath.is_file():
			self.player.set_property('uri', filepath.absolute().as_uri())
		else:
			self.player.set_property('uri', uri)
		
		self.pause()
		#GLib.timeout_add(500, self.seek, 0)
	
	def play(self):
		self.player.set_state(Gst.State.PLAYING)
		self.emit_current_position()
	
	def pause(self):
		self.player.set_state(Gst.State.PAUSED)
	
	def stop(self):
		self.player.set_state(Gst.State.NULL)
		self.last_player_state = -1
		self.emit('state-changed', self.last_player_state)
	
	def change_volume(self, volume):
		self.player.set_property('volume', volume)
	
	def rewind(self, seconds=5):
		current = self.player.query_position(Gst.Format.TIME)[1] / Gst.SECOND
		self.seek(current - seconds)
	
	def forward(self, seconds=5):
		current = self.player.query_position(Gst.Format.TIME)[1] / Gst.SECOND
		self.seek(current + seconds)
	
	def seek(self, position):
		print("seek to:", position)
		self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, Gst.SECOND * position)
	
	def emit_current_position(self):
		if self.player.target_state not in [Gst.State.PLAYING, Gst.State.PAUSED]: return True
		position = self.player.query_position(Gst.Format.TIME)[1] / Gst.SECOND
		duration = self.player.query_duration(Gst.Format.TIME)[1] / Gst.SECOND
		self.emit('current-position', position, duration)
		return True
	
	@idle_add
	def on_message(self, bus, message):
		t = message.type
		if t == Gst.MessageType.EOS:
			GLib.idle_add(self.progressbar.set_fraction, 1.0)
			self.emit('eos')
		elif t == Gst.MessageType.ERROR:
			err, debug = message.parse_error()
			self.emit('error', err, debug)
			self.stop()
		elif t == Gst.MessageType.STATE_CHANGED:
			if self.player.target_state == Gst.State.NULL:
				new_state = PlayerState.NULL
			#elif self.player.target_state == Gst.State.STOPPED:
			#	new_state = PlayerState.STOP
			elif self.player.target_state == Gst.State.READY:
				new_state = PlayerState.READY
			elif self.player.target_state == Gst.State.PAUSED:
				new_state = PlayerState.PAUSED
			elif self.player.target_state == Gst.State.PLAYING:
				new_state = PlayerState.PLAYING
			else:
				new_state = PlayerState.UNKNOWN
			
			if self.last_player_state != self.player.target_state:
				self.last_player_state = self.player.target_state
				self.emit('state-changed', int(self.last_player_state))
	
	@idle_add
	def on_sync_message(self, bus, message):
		if message.get_structure().get_name() == 'prepare-window-handle':
			imagesink = message.src
			imagesink.set_property('force-aspect-ratio', True)
			xid = self.emit('xid-needed')
			print("xid", xid)
			imagesink.set_window_handle(xid)

GObject.type_register(Player)


if __name__ == '__main__':
	import sys, signal
	from pathlib import Path
	from utils import idle_add
	
	gi.require_version('Gtk', '3.0')
	
	from gi.repository import Gtk, Gdk
	
	window = Gtk.Window()
	vbox = Gtk.VBox()
	drawingarea = Gtk.DrawingArea()
	vbox.pack_end(drawingarea, 0, 0, 0)
	hbox = Gtk.HBox()
	
	#interface.connect('open-url', lambda iface, url: player.open_url(url))
	#interface.connect('play', lambda iface: player.play())
	#interface.connect('pause', lambda iface: player.pause())
	#interface.connect('rewind', lambda iface, seconds: player.rewind(seconds))
	#interface.connect('forward', lambda iface, seconds: player.forward(seconds))
	#interface.connect('stop', lambda iface: player.stop())
	#interface.connect('seek', lambda iface, position: player.seek(position))
	#interface.connect('change-volume', lambda iface, volume: player.change_volume(volume))
	#interface.connect('quit', lambda iface: Gtk.main_quit())
	
	hbox.pack_end(vbox, 0, 0, 0)
	
	window.show_all()
	
	player = Player()
	
	player.connect('state-changed', lambda plyr, state: print("state-changed", state))
	player.connect('current-position', lambda plyer, position, duration: print("current-position", position, duration))
	player.connect('xid-needed', lambda plyer: window.get_property('window').get_xid())
	
	window.connect('destroy', lambda win: Gtk.main_quit())
	
	player.open_url('examplewebm')
	player.play()
	
	@idle_add
	def enable_exceptions():
		signal.signal(signal.SIGTERM, lambda signum, frame: Gtk.main_quit())
		sys.excepthook = lambda *args: (sys.__excepthook__(*args), Gtk.main_quit())
	enable_exceptions()
		
	try:
		Gtk.main()
	except KeyboardInterrupt:
		print()
