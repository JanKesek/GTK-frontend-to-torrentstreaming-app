#!/usr/bin/env python

import os
import gi
import time
from main import Interface
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, Gtk

class GTK_Main(object):

    def __init__(self):
        #window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        #window.set_title("Video-Player")
        #window.set_default_size(300, -1)
        #window.connect("destroy", Gtk.main_quit, "WM destroy")
        interface=Interface("interfacevideo.glade")
        time.sleep(5)
        interface.window1.show_all()

        #vbox = Gtk.VBox()
        #window.add(vbox)
        #hbox=Gtk.HBox()
        #self.entry = Gtk.Entry()
        #vbox.pack_start(hbox, False, False, 0)
        #3hbox.add(self.entry)
        #self.button = Gtk.Button("Start")
        #hbox.pack_start(self.button,False,False,0)
        #self.button.connect("clicked", self.start_stop)
        #self.movie_window=Gtk.DrawingArea()
        #vbox.add(self.button)
        #window.show_all()

        #self.player = Gst.ElementFactory.make("playbin", "player")
        #fakesink = Gst.ElementFactory.make("fakesink", "fakesink")
        #self.player.set_property("video-sink", fakesink)
        #bus = self.player.get_bus()
        #bus.add_signal_watch()
        #bus.connect("message", self.on_message)
        #bus.connect("sync-message::element",self.on_sync_message)

    def start_stop(self, w):
        if self.button.get_label() == "Start":
            filepath = self.entry.get_text().strip()
            if os.path.isfile(filepath):
                filepath = os.path.realpath(filepath)
                self.button.set_label("Stop")
                self.player.set_property("uri", "file://" + filepath)
                self.player.set_state(Gst.State.PLAYING)
            else:
                self.player.set_state(Gst.State.NULL)
                self.button.set_label("Start")

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
            self.button.set_label("Start")
        elif t == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: {}".format(err, debug))
            self.button.set_label("Start")

    def on_sync_message(self, bus, message):
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(self.movie_window.get_property('window').get_xid())

Gst.init(None)
GTK_Main()
GObject.threads_init()
Gtk.main()