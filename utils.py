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


__all__ = 'idle_add', 'PlayerState'


from enum import IntEnum

import gi

gi.require_version('Gtk', '3.0')

from gi.repository import GLib


def idle_add(old_func):
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

