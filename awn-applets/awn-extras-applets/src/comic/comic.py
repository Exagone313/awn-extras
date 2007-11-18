#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
# by Chris Johnson
# Much code was taken from Mike (mosburger) Desjardins <desjardinsmike@gmail.com> 
# Weather applet
#
# This is a comic applet for Avant Window Navigator.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
import sys, os
import gobject
import pygtk
import gtk
from gtk import gdk
import gconf
import awn
import urllib
import cairo
from StringIO import StringIO
import comicdialog
from string import join
#default comic
GETWHAT = 'getdilbert.py'
showhover = True
  
class App (awn.AppletSimple):
    titleText = "Daily Comic"
    gconf_path = "/apps/avant-window-navigator/applets/comic"
    visible = False

    def __init__ (self, uid, orient, height):
        awn.AppletSimple.__init__ (self, uid, orient, height)
        self.height = height
        icon = gdk.pixbuf_new_from_file(os.path.dirname (__file__) + '/images/kmouth.png')
        
        if height != icon.get_height():
            icon = icon.scale_simple(height,height,gtk.gdk.INTERP_BILINEAR)
        self.set_icon(icon)

        self.title = awn.awn_title_get_default ()
        self.dialog = awn.AppletDialog (self)
        self.connect ("button-press-event", self.button_press)
        self.connect ("enter-notify-event", self.enter_notify)
        self.connect ("leave-notify-event", self.leave_notify)
        self.dialog.connect ("focus-out-event", self.dialog_focus_out)
        
        self.gconf_client = gconf.client_get_default()

	# Setup popup menu
    	self.popup_menu = gtk.Menu()
    	dil_item = gtk.MenuItem("Dilbert")
    	pnut_item = gtk.MenuItem("Peanuts")
	born_item = gtk.MenuItem("The Born Loser")
    	wiz_item = gtk.MenuItem("Wizard of ID")
        xkcd_item = gtk.MenuItem("xkcd")
   	showho_item = gtk.CheckMenuItem("Hide Strip on Hover")
        self.popup_menu.append(dil_item)
    	self.popup_menu.append(pnut_item)
	self.popup_menu.append(born_item)
	self.popup_menu.append(wiz_item)
	self.popup_menu.append(xkcd_item)
	self.popup_menu.append(showho_item)
        dil_item.connect_object("activate",self.dil_callback,self)
        pnut_item.connect_object("activate",self.pnut_callback,self)
	born_item.connect_object("activate",self.born_callback,self)
	wiz_item.connect_object("activate",self.wiz_callback,self)
	xkcd_item.connect_object("activate",self.xkcd_callback,self)
	showho_item.connect_object("activate",self.showho_callback,self)
        dil_item.show()
        pnut_item.show()
	born_item.show()
	wiz_item.show()
	xkcd_item.show()
	showho_item.show()

        self.build_dialog()


    def build_dialog(self):
        print "Getting Comic"
        
        getit = 'python ' + os.path.dirname (__file__) + '/' + GETWHAT
        os.system(getit)
        
        self.dialog = awn.AppletDialog (self)
        self.dialog.set_title("Comic")
        
        box = gtk.VBox()
        comic = comicdialog.ComicDialog()
        box.pack_start(comic,False,False,0)
        box.show_all()
        self.dialog.add(box)
        
        self.timer = gobject.timeout_add (3600000, self.build_dialog)
    
    
    def button_press (self, widget, event):
	if event.button == 3:
          # right click
          self.title.hide(self)
          self.visible = False
          self.dialog.hide()
          self.popup_menu.popup(None, None, None, event.button, event.time)
          #print "right click"
        else:
          if self.visible:
            self.dialog.hide()     
            self.title.hide(self)
          else:
            self.title.hide(self)
            self.dialog.show_all()
          #self.visible = False


    def dil_callback(self, widget):
        global GETWHAT
	GETWHAT = 'getdilbert.py'
	self.build_dialog()


    def pnut_callback(self, widget):
	global GETWHAT
	GETWHAT = 'getpeanuts.py'
	self.build_dialog()

    def born_callback(self, widget):
	global GETWHAT
	GETWHAT = 'getborn.py'
	self.build_dialog()

    def wiz_callback(self, widget):
	global GETWHAT
	GETWHAT = 'getwiz.py'
	self.build_dialog()

    def xkcd_callback(self, widget):
	global GETWHAT
	GETWHAT = 'getxkcd.py'
	self.build_dialog()

    def showho_callback(self, widget):
	global showhover
	showhover = not showhover
	

    def dialog_focus_out (self, widget, event):
        self.visible = False
        self.dialog.hide()     
        self.title.show (self, self.titleText)


    def enter_notify (self, widget, event):
        self.title.show (self, self.titleText)
	if showhover:	
	  self.title.hide(self)
	  self.dialog.show_all()
	  self.visible = False

    def leave_notify (self, widget, event):
        self.visible = False
        self.title.hide(self)
	self.dialog.hide()


if __name__ == "__main__":
    awn.init (sys.argv[1:])
    #print "main %s %d %d" % (awn.uid, awn.orient, awn.height)
    applet = App(awn.uid, awn.orient, awn.height)
    awn.init_applet(applet)
    applet.show_all()
    gtk.main()
