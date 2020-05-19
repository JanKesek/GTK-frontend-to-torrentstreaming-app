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


"Utilities for MediaKilla."


__author__ = "Janjk"
__credits__ = ["haael <jid:haael@jabber.at>", "Janjk <jid:jklambda@jabber.hot-chilli.net>"]

__copyright__ = "haael.co.uk/prim LTD"
__license__ = 'GPLv3+'

__version__ = '0.0'
__status__ = 'alpha'


__all__ = 'idle_add', 'PlayerState', 'pastebin_upload', 'enable_exceptions', 'report_exceptions'


from enum import IntEnum


def idle_add(old_func):
	from gi.repository import GLib
	
	def new_func(*args):
		GLib.idle_add(old_func, *args)
	new_func.__name__ = old_func.__name__
	return new_func


class PlayerState(IntEnum):
	UNKNOWN = -1
	NULL = 0
	STOP = 1
	READY = 2
	PAUSED = 3
	PLAYING = 4


def pastebin_upload(log_file):
	"Upload the contents of `log_file` (of type `Path`) to pastebin.com."
	
	import urllib.request, urllib.parse
	
	dev_key = 'cb1bb13415c48e868213c7253ea06e04'
	user_key = 'cb99289ff5d20683b59051f1fecb3e69'
	pastebin_url = 'https://pastebin.com/api/api_post.php'
	
	data = {
		'api_dev_key': dev_key,
		'api_user_key' :user_key,
		'api_paste_code': log_file.read_text(),
		'api_option': 'paste',
		'api_paste_private': '0',
		'api_paste_name': str(log_file),
		'api_paste_expire_date': '1D',
		'api_paste_format': 'text'
	}
	
	with urllib.request.urlopen(pastebin_url, urllib.parse.urlencode(data).encode('utf-8')) as result:
		return result.read().decode('utf-8')


exception_data = None


def enable_exceptions(log):
	import sys, signal
	from gi.repository import Gtk
	
	signal.signal(signal.SIGTERM, lambda signum, frame: Gtk.main_quit())
	def intercept_exception(*args):
		sys.excepthook = sys.__excepthook__
		global exception_data
		exception_data = args
		log.critical("Exception: %s", args[1])
		log.debug("posting Gtk.main_quit")
		Gtk.main_quit()
		log.debug("posted Gtk.main_quit")
	sys.excepthook = intercept_exception


def report_exceptions(log, log_file=None):
	import sys, traceback, logging
	
	if exception_data:
		for line in traceback.format_exception(*exception_data):
			log.error(line)
		logging.shutdown()
		
		if log_file:
			print(pastebin_upload(log_file))
		
		sys.__excepthook__(*exception_data)

