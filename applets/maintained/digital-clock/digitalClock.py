#!/usr/bin/python
#
# Copyright Ryan Rushton  ryan@rrdesign.ca
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor Boston, MA 02110-1301,  USA

import sys
import subprocess

import gobject
import gtk
import awn
from awn.extras import _

import dgClockPref
import dgTime


class App(awn.AppletSimple):

    def __init__(self, canonical_name, uid, panel_id):
        super(App, self).__init__(canonical_name, uid, panel_id)

        self.props.display_name = _('Digital Clock')

        self.dialog_visible = False

        self.prefs = dgClockPref.ClockPrefs(self)
        self.clock = dgTime.dgTime(self.prefs, self)
        self.timer = self.timeout_add_seconds(1, self.clock.update_clock)
        self.connect('button-press-event', self.button_press)

    def timeout_add_seconds(self, seconds, callback):
        if hasattr(gobject, 'timeout_add_seconds'):
            return gobject.timeout_add_seconds(seconds, callback)
        else:
            return gobject.timeout_add(seconds * 1000, callback)

    # Dialog callbacks

    def button_press(self, widget, event):
        if event.button == 3: # right click
            self.prefs.menu.popup(None, None, None, event.button, event.time)
        elif self.dialog_visible:
            self.dialog.hide()
            self.dialog_visible = False
        else:
            self.ensure_dialog_created()
            self.dialog.show_all()
            self.dialog_visible = True

    def ensure_dialog_created(self):
        if not hasattr(self, 'dialog'):
            cal = gtk.Calendar()
            cal.set_display_options(gtk.CALENDAR_SHOW_HEADING |
                                    gtk.CALENDAR_SHOW_DAY_NAMES |
                                    gtk.CALENDAR_SHOW_WEEK_NUMBERS)
            cal.connect('day-selected-double-click',
                        self.startExternalCalendar)

            self.dialog = awn.Dialog(self)
            # for focus-follows-mouse
            #self.dialog.connect('focus-out-event',
            #                    self.dialog_focus_out)
            self.dialog.set_title(_('Calendar'))
            self.dialog.add(cal)

#    def dialog_focus_out(self, widget, event):
#        self.dialog.hide()
#        self.dialog_visible = False

    def startExternalCalendar(self, calendar):
        year, month, day = calendar.get_date()
        data = {
            'year': year,
            'month': month + 1,
            'day': day}
        subprocess.Popen(self.prefs.props.calendar_command % data, shell=True)

if __name__ == '__main__':
    awn.init(sys.argv[1:])
    applet = App('digital-clock', awn.uid, awn.panel_id)
    awn.embed_applet(applet)
    applet.show_all()
    gtk.main()