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


"Pipeline for MediaKilla, torrent player."


__author__ = "Janjk"
__credits__ = ["haael <jid:haael@jabber.at>", "Janjk <jid:jklambda@jabber.hot-chilli.net>"]

__copyright__ = "Copyright © 2020, haael.co.uk/prim LTD"
__license__ = 'GPLv3+'

__version__ = '0.0'
__status__ = 'alpha'


__all__ = 'PlayerTorrent',


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


from player import Player, __version__ as player_version
if player_version != __version__:
	raise ImportError(f"Wrong version of module `player`. Expected '{__version__}', got '{player_version}'.")


@GObject.type_register
class PlayerTorrent(Player):
	#COMMAND = "appsrc name=AppSrc emit-signals=True is-live=False ! queue max-size-buffers=4 ! decodebin ! videoconvert ! autovideosink"
	#COMMAND = "appsrc name=AppSrc emit-signals=True is-live=False ! queue max-size-buffers=4 ! decodebin name=dec \ dec. ! videoconvert ! autovideosink .dec \
	#			queue ! audioconvert ! audioresample ! autoaudiosink \ dec."
	#COMMAND = """
	#	appsrc name=AppSrc emit-signals=true is-live=true ! 
#		qtdemux name=demuxer  demuxer. ! queue ! avdec_h264 ! autovideosink  demuxer.audio_0 !  queue ! audioconvert ! audioresample ! volume volume=0.5 ! autoaudiosink
#				"""
	COMMAND= """
	appsrc name=AppSrc emit-signals=true is-live=false ! typefind ! qtdemux name=demuxer \
	demuxer. ! videoconvert ! queue ! autovideosink \
	demuxer.audio_0 ! audioconvert ! queue ! volume volume=5  ! autoaudiosink 
		"""

	#demuxer.decodebin
	MAX_BUFFER_SIZE = 16 * 1024
	
	def __init__(self):		
		super().__init__()
		
		self.appsrc = self.player.get_by_name('AppSrc')
		self.appsrc.set_property('format', Gst.Format.BYTES)
		self.appsrc.set_property('block', False)
		
		conn1 = self.appsrc.connect('need-data', self.need_data)
		conn2 = self.appsrc.connect('enough-data', self.enough_data)
		conn3 = self.appsrc.connect('seek-data', self.seek_data)
		
		self.appsrc_connections = frozenset([conn1, conn2, conn3])
		
		self.data_needed = 0
		self.data_sending = None
		self.source_file = None
	
	def __del__(self):
		try:
			if self.data_sending != None:
				GLib.source_remove(self.data_sending)
		except AttributeError as error:
			log.warning("Error in PlayerTorrent finalizer: %s", str(error))
		
		try:
			for conn in self.appsrc_connections:
				self.appsrc.disconnect(conn)
		except AttributeError as error:
			log.warning("Error in PlayerTorrent finalizer: %s", str(error))
		
		try:
			super().__del__()
		except AttributeError as error:
			log.warning("Error in PlayerTorrent finalizer: %s", str(error))
	
	def create_pipeline(self):
		log.info("Creating the torrent player.")
		return Gst.parse_launch(self.COMMAND)
	
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
	
	def data_available(self, position):
		"Number of bytes available at `position`. Returns 0 if none."
		return 1024 * 4 # TODO: finish implementation
	
	@idle_add
	def data_received(self, offset, length):
		"Triggered when a block of data is received from Torrent."
		if offset <= self.source_file.tell() < offset + length and self.data_needed > 0 and self.data_sending == None:
			log.info("Received block at position %d (size %d), resuming playback.")
			# TODO: emit `unchoke` signal
			self.data_sending = GLib.io_add_watch(self.source_file, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self.send_data)
	
	def send_data(self, fd, condition):
		log.debug("send_data: data_needed=%d", self.data_needed)
		
		if GLib.IO_IN & condition:
			data_size = min(self.MAX_BUFFER_SIZE, self.data_available(self.source_file.tell()), self.appsrc.get_property('max_bytes'), self.data_needed)
			
			if data_size > 0:
				chunk = self.source_file.read(data_size)
			else:
				log.info("No data available, pausing playback.")
				# TODO: emit `choke` signal
				self.data_sending = None
				return False
			
			if chunk:
				log.debug("send_data: push buffer %d", len(chunk))
				
				self.appsrc.emit('push_buffer', Gst.Buffer.new_wrapped(chunk))
				
				self.data_needed -= len(chunk)
				if self.data_needed <= 0:
					self.data_needed = 0
					self.data_sending = None
					return False
			else:
				log.info("send_data: Reached end of stream.")
				
				self.appsrc.emit('end-of-stream')
				self.data_needed = 0
				self.data_sending = None
				return False
		
		elif (GLib.IO_HUP | GLib.IO_ERR) & condition:
			log.error("send_data: Error while reading source file.")
			
			self.source_file.close()
			self.source_file = None
			self.file_size = 0
			self.appsrc.set_stream_size(0)
			self.data_needed = 0
			self.data_sending = None
			#TODO: emit error signal
			return False
		
		return True
	
	@idle_add
	def need_data(self, appsrc, length):
		log.debug("need_data %d", length)
		
		self.data_needed += length
		
		if self.data_sending == None:
			self.data_sending = GLib.io_add_watch(self.source_file, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self.send_data)
	
	@idle_add
	def enough_data(self):
		log.debug("enough_data")
		
		if self.data_sending != None:
			GLib.source_remove(self.data_sending)
			self.data_sending = None
			self.data_needed = 0
	
	@idle_add
	def seek_data(self, offset):
		log.debug("seek_data %d", offset)
		
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
	drawingarea = Gtk.DrawingArea()
	window.add(drawingarea)
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
