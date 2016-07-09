#!/usr/bin/env python2

# Copyright (C) 2016 Elouan Martinet <exa@elou.world>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import os

import pygtk
pygtk.require("2.0")
import gtk
import cairo
from awn.extras import _, awnlib, __version__

import time


applet_name = "Simple Digital Clock"
applet_name_short = "simple-digital-clock"
applet_description = "Digital clock that displays date and/or time " +\
	"using strftime format."
applet_theme_logo = "awn-applet-digital-clock"
applet_additional_authors = []

time_format_default = "%H:%M:%S"
refresh_interval_default = 200
refresh_interval_minimum = 100
refresh_interval_maximum = 60000
ui_file = applet_name_short + ".glade"

# TODO: let the user choose the timezone.
# TODO: calendar

class SimpleDigitalClockApplet:

	def __init__(self, applet):
		self.applet = applet
		self.settings = {}
		self.settings_dialog_window = None

		# load settings, catch possible Exception
		self.load_setting("time_format", time_format_default)
		self.load_setting("refresh_interval", refresh_interval_default)
		self.sanitize_refresh_internal()

		# start display and refresh timer
		self.load_display()
		self.timer = applet.timing.register(self.refresh, self.settings["refresh_interval"] / 1000)

	def load_setting(self, setting_name, default_value = False):
		setting_name = str(setting_name)
		try:
			self.settings[setting_name] = self.applet.settings[setting_name]
		except:
			# print applet name for easier debugging
			print "... in " + applet_name_short + ", fallback to default"
			self.settings[setting_name] = default_value

	def sanitize_refresh_internal(self):
		if(self.settings["refresh_interval"] < refresh_interval_minimum):
			self.settings["refresh_interval"] = refresh_interval_minimum
		else if(self.settings["refresh_interval"] > refresh_interval_maximum):
			self.settings["refresh_interval"] = refresh_interval_maximum

	def get_current_time(self, timezone = None): # TODO timezone
		return time.strftime(self.setting["time_format"])

	@staticmethod
	def sanitize_int(str_int = 0):
		try:
			return int(str_int)
		except:
			return 0

	def load_display(self):
		#size = self.applet.get_size()
		#surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
		self.display = cairo.Context()

		self.displayed_text = self.get_current_time()
		self.display.show_text(self.displayed_text)
		self.applet.icon.set(self.display)

	def refresh(self):
		new_text = self.get_current_time()
		if self.displayed_text is not new_text:
			self.displayed_text = new_text
			self.display.show_text(self.displayed_text)

	def settings_dialog(self):
		if self.settings_dialog_window is not None:
			self.settings_dialog_window.grab_focus()
			self.settings_dialog_window.show_all()
			return

		builder = gtk.Builder()
		builder.add_from_file(os.path.join(os.path.dirname(__file__), ui_file))
		if builder is None:
			print "UI file " + ui_file + " not found."
			return

		# get objects
		label_format = builder.get_object("label_format")
		label_interval = builder.get_object("label_interval")
		label_timezone = builder.get_object("label_timezone")
		entry_format = builder.get_object("entry_format")
		entry_interval = builder.get_object("entry_interval")
		entry_timezone = builder.get_object("entry_timezone")
		button_close = builder.get_object("button_close")
		button_ok = builder.get_object("button_ok")
		button_apply = builder.get_object("button_apply")

		# ensure they exist (assuming their type are correct)
		if None in (label_format, label_interval, label_timezone,
				entry_format, entry_interval, entry_timezone,
				button_close, button_ok, button_apply):
			print "UI file " + ui_file + " malformed."
			return

		# set values from translation and saved settings
		label_format.set_property("label", _("Format (see strftime)"))
		label_interval.set_property("label", _("Refresh interval (ms)"))
		label_timezone.set_property("label", _("Timezone"))
		entry_format.set_property("text", self.settings["time_format"])
		entry_interval.set_property("text", self.settings["refresh_interval"])
		entry_timezone.set_property("text", "(not yet)") # TODO timezone

		# save important objects
		self.entry_format = entry_format
		self.entry_interval = entry_interval
		self.entry_timezone = entry_timezone

		# create window
		self.settings_dialog_window = self.applet.dialog.new("preferences")
		builder.get_object("dialog-vbox1").reparent(self.settings_dialog_window.vbox)
		self.settings_dialog_window.show_all()

		# add events
		self.settings_dialog_window.connect("destroy", self.trigger_cancel, self)
		button_close.connect("clicked", self.trigger_cancel)
		button_ok.connect("clicked", self.trigger_ok)
		button_apply.connect("clicked", self.trigger_apply)

	def trigger_apply(self, widget):
		self.settings["time_format"] = self.applet.settings["time_format"] = self.entry_format.get_property("text")

		self.settings["refresh_interval"] = self.sanitize_int(self.entry_interval.get_property("text"))
		sanitize_refresh_internal()
		self.applet.settings["refresh_interval"] = self.settings["refresh_interval"]

		self.timer.change_interval(self.settings["refresh_interval"] / 1000)
		# TODO timezone

	def trigger_cancel(self, widget):
		self.settings_dialog_window.hide()

	def trigger_ok(self, widget):
		self.trigger_apply()
		self.trigger_cancel()


if __name__ == "__main__":
	awnlib.init_start(SimpleDigitalClockApplet, {
		"name": _(applet_name),
		"short": applet_name_short,
		"version": __version__,
		"description": _(applet_description),
		"theme": applet_theme_logo,
		"author": "Elouan Martinet <exa@elou.world>",
		"copyright-year": "2016",
		"authors": ["Elouan Martinet <exa@elou.world>"] + applet_additional_authors
	})