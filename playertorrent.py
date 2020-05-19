import gi
import logging
from utils import *
from gi.repository import Gst,Gtk, Gdk,GObject,GLib

gi.require_version('Gtk', '3.0')
	
GLib.threads_init()
Gst.init(None)

from player import Player
from networking.bittorrent import start_download
#command="appsrc emit-signals=True is-live=True \
#caps=video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! \
#queue max-size-buffers=4 ! videoconvert ! autovideosink"
command="videotestsrc num-buffers=100 ! \
capsfilter caps=video/x-raw,format=RGB,width=640,height=480 ! \
appsink emit-signals=True"

CAPS= "video/x-raw,format=RGB,width=640,height=480,framerate=30/1"
@GObject.type_register
class PlayerTorrent(Player):
	def __init__(self):
		#log.info("Creating the torrent player.")	
		GObject.Object.__init__(self)
		
		
		#self.player = Gst.ElementFactory.make("playbin", "player")
		self.position_sending = GLib.timeout_add(1000, self.emit_current_position)
		self.last_player_state = PlayerState.UNKNOWN

		self.pipeline=Gst.Pipeline(command)
		self.pipeline._on_pipeline_init=self.on_pipeline_init.__get__(self.pipeline)
		#self.pipeline.startup()
		self.bus = self.pipeline.get_bus()
		self.bus.add_signal_watch()
		self.bus.enable_sync_message_emission()
		
		conn1 = self.bus.connect('message', self.on_message)
		conn2 = self.bus.connect('sync-message::element', self.on_sync_message)
		self.bus_connections = frozenset([conn1, conn2])
		self.offset=0
	def open_url(self, uri):
		start_download([uri])

	def play(self):
		print("PLAY FROM PLAYERTORRENT")
	
	def pause(self):
		pass
	def stop(self):
		pass
	def change_volume(self, volume):
		pass
	def rewind(self, seconds=5):
		pass

	def forward(self, seconds=5):
		pass

	def seek(self, position):
		pass

	def emit_current_position(self):
		pass

	def extract_bytes_from_file(self,size):
		with open("test_bittorrent/data/costam/file","rb") as bf:
			bf.seek(self.offset,self.offset)
			chunk=bf.file_read(size)
			self.offset+=size
			return chunk
	def extract_buffer(self,sample) -> np.ndarray:
    	buffer = sample.get_buffer()  # Gst.Buffer
    	print(buffer.pts, buffer.dts, buffer.offset)

    	caps_format = sample.get_caps().get_structure(0)  # Gst.Structure

    	video_format = GstVideo.VideoFormat.from_string(caps_format.get_value('format'))
		w, h = caps_format.get_value('width'), caps_format.get_value('height')
    	c = utils.get_num_channels(video_format)

    	buffer_size = buffer.get_size()
		array=self.extract_bytes_from_file(buffer_size)
		return array
    #shape = (h, w, c) if (h * w * c == buffer_size) else buffer_size
    #array = np.ndarray(shape=shape, buffer=buffer.extract_dup(0, buffer_size),
    #                   dtype=utils.get_np_dtype(video_format))

    	#return np.squeeze(array)  # remove single dimension if exists


	#@idle_add
	#def on_sync_message(self, bus, message):
	#	pass
	def on_buffer(self,sink, data):
		sample = sink.emit("pull-sample")  # Gst.Sample
		if isinstance(sample, Gst.Sample):
			array = extract_buffer(sample)
			print("Received {type} with shape {shape} of type {dtype}".format(type=type(array),
                                                                        shape=array.shape,
                                                                        dtype=array.dtype))
			return Gst.FlowReturn.OK
		return Gst.FlowReturn.ERROR		
	def on_pipeline_init(self):
		#self.appsrc=self.get_by_cls(GstApp.AppSrc)[0]
		#self.appsrc.set_property("format", Gst.Format.TIME)        
		#self.appsrc.set_property("block", True)
		#self.appsrc.set_caps(Gst.Caps.from_string(CAPS))
		self.appsink=self.get_by_cls(GstApp.AppSink)[0]
		self.appsink.connect("new-sample",self.on_buffer)
		while not self.pipeline.is_done:
			time.sleep(.1)
if __debug__ and __name__ == '__main__':
	from pathlib import Path
	from utils import idle_add, enable_exceptions, report_exceptions
	import time
	
	log = logging.getLogger('player')

	log_file = Path('/tmp/mediakilla-player.log')
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
