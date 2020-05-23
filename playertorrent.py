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

#    Copyright © 2020, haael.co.uk/prim LTD


"Player view for MediaKilla."


__author__ = "Janjk"
__credits__ = ["haael <jid:haael@jabber.at>", "Janjk <jid:jklambda@jabber.hot-chilli.net>"]

__copyright__ = "Copyright © 2020, haael.co.uk/prim LTD"
__license__ = 'GPLv3+'

__version__ = '0.0'
__status__ = 'alpha'


__all__ = 'Player',


import logging

log = logging.getLogger('playertorrent')
log.setLevel(logging.DEBUG)
if __debug__:
	log.addHandler(logging.StreamHandler())

import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import GObject, GLib, Gst, GstVideo

from utils import *


if __name__ == '__main__':
	GLib.threads_init()
	Gst.init(None)
elif not Gst.is_initialized():
	raise ImportError("GStreamer must be initialized with `Gst.init(sys.argv)` before you attempt to import this module.")


from player import Player


@GObject.type_register
class PlayerTorrent(Player):
	command = "appsrc name=AppSrc emit-signals=True is-live=False ! queue max-size-buffers=4 ! decodebin ! videoconvert ! autovideosink"
	
	def __init__(self):		
		super().__init__()
		
		self.appsrc = self.player.get_by_name('AppSrc')
		self.appsrc.set_property("format", Gst.Format.BYTES)
		self.appsrc.set_property("block", False)
		
		self.appsrc.connect('need-data', self.need_data)
		self.appsrc.connect('enough-data', self.enough_data)
		self.appsrc.connect('seek-data', self.seek_data)
		
		self.data_needed = 0
		self.data_sending = None
		self.source_file = None
	
	def create_pipeline(self):
		log.info("Creating the torrent player.")
		return Gst.parse_launch(self.command)
	
	def open_url(self, uri):
		#start_download([uri])
		from pathlib import Path
		
		if self.source_file != None:
			self.source_file.close()
			self.source_file = None
			self.file_size = 0
		
		path = Path(uri)
		if path.is_file():
			self.source_file = path.open('rb')
			self.file_size = path.stat().st_size
			try:
				self.appsrc.set_stream_size(self.file_size)
			except AttributeError:
				pass
	
	def send_data(self, fd, condition):
		#print("send_data", self.appsrc.get_property('max_bytes'), self.data_needed)
		if GLib.IO_IN & condition:
			chunk = self.source_file.read(min(self.appsrc.get_property('max_bytes'), self.data_needed))
			if chunk:
				#print("send_data: push buffer", len(chunk))
				self.appsrc.emit('push_buffer', Gst.Buffer.new_wrapped(chunk))
				self.data_needed -= len(chunk)
				if self.data_needed <= 0:
					self.data_needed = 0
					self.data_sending = None
					return False
			else:
				#print("send_data: end of stream")
				self.appsrc.emit('end-of-stream')
				self.data_needed = 0
				self.data_sending = None
				return False
		elif (GLib.IO_HUP | GLib.IO_ERR) & condition:
			#print("send_data: error")
			self.source_file.close()
			self.source_file = None
			self.file_size = 0
			self.appsrc.set_stream_size(0)
			self.data_needed = 0
			self.data_sending = None
			return False
		return True
	
	@idle_add
	def need_data(self, appsrc, length):
		#print("need_data", length)
		self.data_needed += length
		if self.data_sending == None:
			self.data_sending = GLib.io_add_watch(self.source_file, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self.send_data)
	
	@idle_add
	def enough_data(self):
		#print("enough_data")
		if self.data_sending != None:
			GLib.source_remove(self.data_sending)
			self.data_sending = None
			self.data_needed = 0
	
	@idle_add
	def seek_data(self, offset):
		#print("seek_data", appsrc)
		if self.source_file != None:
			self.source_file.seek(offset)
	
	#def on_pipeline_init(self):
	#	print("on_pipeline_init")
	#	
	#	self.appsrc = self.get_by_cls(GstApp.AppSrc)[0]
	#	self.appsrc.set_property("format", Gst.Format.BYTES)
	#	self.appsrc.set_property("block", False)
	#	#self.appsrc.set_caps(Gst.Caps.from_string(self.CAPS))
	#	
	#	self.appsrc.connect('need-data', self.data_needed)
	#	self.appsrc.connect('enough-data', self.enough_data)
	#	self.appsrc.connect('seek-data', self.seek_data)
	#	
	#	#self.appsrc.set_stream_size(self.file_size)
	#	
	#	#while not self.pipeline.is_done:
	#	#	time.sleep(.1)


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	from utils import idle_add, enable_exceptions, report_exceptions
	import time
	
	gi.require_version('Gtk', '3.0')
	
	from gi.repository import Gtk, Gdk
	
	log_file = Path('/tmp/mediakilla-playertorrent.log')
	logging.basicConfig(filename=str(log_file), filemode='w')
	log.info("Start: %s", time.strftime('%Y-%m-%d %H:%M:%S'))
	
	window = Gtk.Window()
	vbox = Gtk.VBox()
	drawingarea = Gtk.DrawingArea()
	vbox.pack_end(drawingarea, 0, 0, 0)
	hbox = Gtk.HBox()
		
	hbox.pack_end(vbox, 0, 0, 0)
	
	window.show_all()
	
	player = PlayerTorrent()
	
	player.connect('state-changed', lambda plyr, state: log.info("state-changed %s", state))
	player.connect('current-position', lambda plyr, position, duration: log.info("current-position %f %f", position, duration))
	player.connect('xid-needed', lambda plyr: window.get_property('window').get_xid())
	player.connect('eos', lambda plyr: log.info("eos"))
	
	window.connect('destroy', lambda win: Gtk.main_quit())
	
	player.open_url('examplewebm')
	player.play()
	
	idle_add(enable_exceptions)(log)
	
	try:
		Gtk.main()
	except KeyboardInterrupt:
		print()
	
	log.info("Stop: %s", time.strftime('%Y-%m-%d %H:%M:%S'))
	
	report_exceptions(log, log_file)
