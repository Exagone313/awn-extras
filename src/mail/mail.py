# Copyright (C) 2008  Pavel Panchekha <pavpanchekha@gmail.com>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import email
import gettext
import locale
import os
import re
import time
import subprocess

import pygtk
pygtk.require("2.0")
import gtk
from awn.extras import awnlib
from awn.extras import defs

APP = "awn-extras-applets"
gettext.bindtextdomain(APP, defs.GETTEXTDIR)
gettext.textdomain(APP)
_ = gettext.gettext

themes_dir = os.path.join(os.path.dirname(__file__), "Themes")


def strMailMessages(num):
    return gettext.ngettext("You have %d new message", "You have %d new messages", num) % num


def strMessages(num):
    return gettext.ngettext("%d unread message", "%d unread messages", num) % num

def get_label_entry(text, label_group=None, entry_group=None):
    hbox = gtk.HBox(False, 12)

    label = gtk.Label(text)
    label.set_alignment(0.0, 0.5)
    hbox.pack_start(label, False)

    entry = gtk.Entry()
    hbox.pack_start(entry)

    if label_group is not None:
        label_group.add_widget(label)

    if entry_group is not None:
        entry_group.add_widget(entry)

    return (entry, hbox)

class MailApplet:
    def __init__(self, applet):
        self.awn = applet

        default_values = {
            "backend": "GMail",
            "theme": "Tango",
            "email-client": "evolution -c mail",
            "hide": False,
            "show-network-errors": True
        }
        
        applet.settings.load(default_values)

        self.back = getattr(Backends(), self.awn.settings["backend"])
        self.theme = self.awn.settings["theme"]
        self.emailclient = self.awn.settings["email-client"]
        self.hide = self.awn.settings["hide"]
        self.showerror = self.awn.settings["show-network-errors"]

        self.__setIcon("login")

        self.awn.tooltip.set(_("Mail Applet (Click to Log In)"))

        self.setup_context_menu()

        self.awn.errors.module(globals(), "feedparser")

        self.login()
    
    def login(self, force=False):
        self.__setIcon("login")
        if force:
            return self.setup_login_dialog()
        # If we're forcing initiation, just draw the dialog
        # We wouldn't be forcing if we want to use the saved login token

        try:
            token = self.awn.settings["login-token"]
        except: # You know what? too bad. No get_null, no exception handling
            token = 0

        if token == 0:
           return self.login(True)
        # Force login if the token is 0, which we take to mean that there
        # is no login information. We'd delete the key, but that's not
        # always supported.

        key = self.awn.keyring.from_token(token)

        self.submitPWD(key)

    def logout(self):
        if hasattr(self, "timer"):
            self.timer.stop()
        self.__setIcon("login")
        self.awn.settings["login-token"] = 0

    def submitPWD(self, key):
        self.mail = self.back(key) # Login

        try:
            self.mail.update() # Update
        except RuntimeError:
            self.setup_login_dialog(True)

        else:
            self.awn.notify.send(_("Mail Applet"), \
                _("Logging in as %s") % key.attrs["username"], \
                self.__getIconPath("login", full=True))

            # Login successful
            self.__setIcon("read")

            self.awn.settings["login-token"] = key.token

            self.timer = self.awn.timing.register(self.refresh, 300)
            self.refresh(hide=False)

    def refresh(self, x=None, hide=True):
        oldSubjects = self.mail.subjects

        try:
            self.mail.update()
        except RuntimeError, (err):
            self.__setIcon("error")

            if self.showerror:
                self.awn.errors.general(err)
            return

        diffSubjects = [i for i in self.mail.subjects if i not in oldSubjects]
        
        if len(diffSubjects) > 0:
            msg = strMailMessages(len(diffSubjects)) + "\n" + "\n".join(diffSubjects)
            self.awn.notify.send(_("New Mail - Mail Applet"), msg, self.__getIconPath("unread", full=True))

        self.awn.tooltip.set(strMessages(len(self.mail.subjects)))
        
        self.__setIcon(len(self.mail.subjects) > 0 and "unread" or "read")

        if hide and self.hide and len(self.mail.subjects) == 0:
            self.awn.icon.hide()
            self.awn.dialog.hide()

        elif hide:
            self.awn.show()

        self.drawMainDlog()

    def __setIcon(self, name):
        self.awn.icon.file(self.__getIconPath(name))
    
    def __getIconPath(self, name, full=False):
        if full:
            return os.path.join(themes_dir, self.theme, name + ".svg")
        else:
            return os.path.join("Themes", self.theme, name + ".svg")

    def __showWeb(self):
        if hasattr(self.mail, "showWeb"):
            self.mail.showWeb()
        elif hasattr(self.mail, "url"):
            subprocess.Popen(["xdg-open", self.mail.url()])

    def __showDesk(self):
        if hasattr(self.mail, "showDesk"):
            self.mail.showDesk()
        else:
            if " " in self.emailclient:
                subprocess.Popen(self.emailclient, shell=True)
            else:
                subprocess.Popen(self.emailclient)
            # Now if xdg-open had an option to just open the email client,
            # not start composing a message, that would be just wonderful.

    def drawMainDlog(self):
        dialog = self.awn.dialog.new("main", strMessages(len(self.mail.subjects)))

        vbox = gtk.VBox()
        dialog.add(vbox)

        if len(self.mail.subjects) > 0:
            tbl = gtk.Table(len(self.mail.subjects), 2)
            tbl.set_col_spacings(10)
            for i in xrange(len(self.mail.subjects)):
                
                label = gtk.Label("<b>"+str(i+1)+"</b>")
                label.set_use_markup(True)
                tbl.attach(label, 0, 1, i, i+1)
                
                label = gtk.Label(self.mail.subjects[i])
                label.set_use_markup(True)
                tbl.attach(label, 1, 2, i, i+1)
                #print "%d: %s" % (i+1, self.mail.subjects[i])
            vbox.add(tbl)
        else:
            label = gtk.Label("<i>" + _("Hmmm, nothing here") + "</i>")
            label.set_use_markup(True)
            vbox.add(label)

        buttons = []

        if hasattr(self.mail, "url") or hasattr(self.mail, "showWeb"):
            # Don't show the button if it doesn't do anything

            # This'll be the "show web interface" button
            b = gtk.Button()
            b.set_relief(gtk.RELIEF_NONE) # Found it; that's a relief
            b.set_image(gtk.image_new_from_stock(gtk.STOCK_NETWORK, gtk.ICON_SIZE_BUTTON))
            b.set_tooltip_text(_("Open Web Mail"))
            b.connect("clicked", lambda x: self.__showWeb())
            buttons.append(b)

        # This is the "show desktop client" button
        b = gtk.Button()
        b.set_relief(gtk.RELIEF_NONE)
        b.set_image(gtk.image_new_from_stock(gtk.STOCK_DISCONNECT, gtk.ICON_SIZE_BUTTON))
        b.set_tooltip_text(_("Open Desktop Client"))
        b.connect("clicked", lambda x: self.__showDesk())
        buttons.append(b)

        # Refresh button
        b = gtk.Button()
        b.set_relief(gtk.RELIEF_NONE)
        b.set_image(gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_BUTTON))
        b.set_tooltip_text(_("Refresh"))
        b.connect("clicked", lambda x: self.refresh())
        buttons.append(b)

        # Log out
        b = gtk.Button()
        b.set_relief(gtk.RELIEF_NONE)
        b.set_image(gtk.image_new_from_stock(gtk.STOCK_STOP, gtk.ICON_SIZE_BUTTON))
        b.set_tooltip_text(_("Log Out"))
        b.connect("clicked", lambda x: self.logout())
        b.connect("clicked", lambda x: self.setup_login_dialog())

        buttons.append(b)
        hbox_buttons = gtk.HBox()
        for i in buttons:
            hbox_buttons.add(i)
        vbox.add(hbox_buttons)

    def login_get_widgets(self, vbox, *groups):
        for widget in self.login_widgets:
            widget.destroy()

        if hasattr(self.back, "drawLoginWindow"):
            t = self.back.drawLoginWindow(*groups)
            self.login_widgets.append(t["layout"])
            vbox.add(t["layout"])
        else:
            usrE, box = get_label_entry(_("Username:"), *groups)
            vbox.add(box)
            self.login_widgets.append(box)

            pwdE, box = get_label_entry(_("Password:"), *groups)
            pwdE.set_visibility(False)
            vbox.add(box)
            self.login_widgets.append(box)
            
            t = {}

            t["callback"] = \
                lambda widgets, awn: awn.keyring.new("Mail Applet - %s(%s)" \
                % (widgets[0].get_text(), self.awn.settings["backend"]), \
                widgets[1].get_text(), \
                {"username": widgets[0].get_text()}, "network")

            t["widgets"] = [usrE, pwdE]

        vbox.show_all()

        return t

    def setup_login_dialog(self, error=False):
        dialog = self.awn.dialog.new("main", _("Log In"))
        vbox = gtk.VBox(spacing=12)
        vbox.set_border_width(6)
        dialog.add(vbox)

        #Make all the labels the same size
        label_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        #Make the combo box and all the entries the same size
        entry_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        #Display an error message if there is one
        if error:
            image = gtk.image_new_from_stock(gtk.STOCK_DIALOG_ERROR, gtk.ICON_SIZE_MENU)
            label = gtk.Label("<b>" + _("Wrong username or password") + "</b>")
            label.set_use_markup(True)

            hbox = gtk.HBox(False, 6)
            hbox.pack_start(image, False)
            hbox.pack_start(label)

            #Align the image and label in the center, with the image
            #right next to the label
            hboxbox = gtk.HBox(False)
            hboxbox.pack_start(hbox, True, False)

            vbox.add(hboxbox)

        #Allow user to change the backend in the login dialog
        def changed_backend_cb(combobox, label_group, entry_group):
            backend = combobox.get_active()
            
            if backend != -1:
                backends = [i for i in dir(Backends) if i[:2] != "__"]
                self.awn.settings["backend"] = backends[backend]
                self.back = getattr(Backends(), backends[backend])
                self.login_get_widgets(vbox, label_group, entry_group)

        label_backend = gtk.Label(_("Type:"))
        label_backend.set_alignment(0.0, 0.5)
        label_group.add_widget(label_backend)

        backend = gtk.combo_box_new_text()
        backend.set_title(_("Backend"))
        backends = [i for i in dir(Backends) if i[:2] != "__"]
        for i in backends:
            backend.append_text(getattr(Backends(), i).title)
        backend.set_active(backends.index(self.awn.settings["backend"]))
        entry_group.add_widget(backend)
        backend.connect("changed", changed_backend_cb, label_group, entry_group)

        hbox_backend = gtk.HBox(False, 12)
        hbox_backend.add(label_backend)
        hbox_backend.pack_start(backend)

        vbox.add(hbox_backend)

        self.login_widgets = []
        t = self.login_get_widgets(vbox, label_group, entry_group)

        image_login = gtk.image_new_from_stock(gtk.STOCK_NETWORK, gtk.ICON_SIZE_BUTTON)
        submit_button = gtk.Button(label=_("Log In"), use_underline=False)
        submit_button.set_image(image_login)
        def onsubmit(x=None, y=None):
            self.awn.dialog.toggle("main", "hide")
            self.submitPWD(t["callback"](t["widgets"], self.awn))
        submit_button.connect("clicked", onsubmit)

        hbox_login = gtk.HBox(False, 0)
        hbox_login.pack_start(submit_button, True, False)
        vbox.pack_end(hbox_login)

        self.awn.dialog.toggle("main", "show")
    
    def setup_context_menu(self):
        prefs_vbox = self.awn.dialog.new("preferences").vbox
        vbox = gtk.VBox(spacing=18)
        prefs_vbox.add(vbox)
        vbox.set_border_width(6)
        
        vbox_mail = awnlib.create_frame(vbox, "Mail")
        
        hbox_backend = gtk.HBox(False, 12)
        vbox_mail.add(hbox_backend)

        label_backend = gtk.Label(_("Type:"))
        label_backend.set_alignment(0.0, 0.5)
        hbox_backend.pack_start(label_backend, False)
        
        backend = gtk.combo_box_new_text()
        backend.set_title(_("Backend"))
        backends = [i for i in dir(Backends) if i[:2] != "__"]
        for i in backends:
            backend.append_text(getattr(Backends(), i).title)
        backend.set_active(backends.index(self.awn.settings["backend"]))
        backend.connect("changed", self.changed_backend_cb)
        hbox_backend.pack_start(backend)
        
        hbox_client = gtk.HBox(False, 12)
        vbox_mail.add(hbox_client)

        label_client = gtk.Label(_("Email Client:"))
        label_client.set_alignment(0.0, 0.5)
        hbox_client.pack_start(label_client, False)
        
        email = gtk.Entry()
        email.set_text(self.emailclient)
        email.connect("changed", self.changed_client_cb)
        hbox_client.pack_start(email)
        
        vbox_display = awnlib.create_frame(vbox, "Display")
        
        hbox_theme = gtk.HBox(False, 12)
        vbox_display.add(hbox_theme)

        label_theme = gtk.Label(_("Theme:"))
        label_theme.set_alignment(0.0, 0.5)
        hbox_theme.pack_start(label_theme, False)
        
        theme = gtk.combo_box_new_text()
        theme.set_title(_("Theme"))
        themes = [i for i in os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Themes"))]
        for i in themes:
            theme.append_text(i)
        theme.connect("changed", self.changed_theme_cb)
        theme.set_active(themes.index(self.theme))
        hbox_theme.pack_start(theme)
        
        hidden = gtk.CheckButton(label=_("Hide applet icon if no new messages"))
        hidden.set_active(self.hide)
        hidden.connect("toggled", self.toggled_hide_cb)
        vbox_display.add(hidden)

        show_errors = gtk.CheckButton(label=_("Alert on Network Errors"))
        show_errors.set_active(self.showerror)
        show_errors.connect("toggled", self.toggled_show_errors_cb)
        vbox_display.add(show_errors)

        size_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        size_group.add_widget(label_backend)
        size_group.add_widget(label_client)
        size_group.add_widget(label_theme)

        size_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        size_group.add_widget(backend)
        size_group.add_widget(email)
        size_group.add_widget(theme)
    
    def toggled_hide_cb(self, button):
        self.awn.settings["hide"] = self.hide = button.get_active()

        if hasattr(self, "mail"):
            if self.hide and len(self.mail.subjects) == 0:
                self.awn.icon.hide()

            else:
                self.awn.show()

    def toggled_show_errors_cb(self, button):
        self.awn.settings["show-network-errors"] = self.showerror = button.get_active()
    
    def changed_theme_cb(self, combobox):
        theme = combobox.get_active_text()
        if theme != -1:
            self.awn.settings["theme"] = self.theme = theme
            
            if hasattr(self, "mail"):
                self.__setIcon(len(self.mail.subjects) > 0 and "unread" or "read")
            else:
                self.__setIcon("login")
    
    def changed_backend_cb(self, combobox):
        backend = combobox.get_active()
        
        if backend != -1:
            backends = [i for i in dir(Backends) if i[:2] != "__"]
            self.awn.settings["backend"] = backends[backend]
            self.back = getattr(Backends(), backends[backend])
            self.logout()
    
    def changed_client_cb(self, entry):
        self.awn.settings["email-client"] = self.emailclient = entry.get_text()

class MailItem:
    def __init__(self, subject, author):
        self.subject = subject
        self.author = author

class Backends:
    class GMail:
        title = "Gmail"

        def __init__(self, key):
            self.key = key

        def url(self):
            return "http://mail.google.com/mail/"

        def update(self):
            f = feedparser.parse( \
                "https://%s:%s@mail.google.com/gmail/feed/atom" \
                 % (self.key.attrs["username"], self.key.password))

            if "bozo_exception" in f.keys():
                raise RuntimeError, _("There seem to be problems with our \
connection to your account. Your best bet is probably \
to log out and try again.")
            # Hehe, Google is funny. Bozo exception

            t = []
            self.subjects = []
            for i in f.entries:
                i.title = self.__cleanGmailSubject(i.title)
                t.append(MailItem(i.title, i.author))
                self.subjects.append(i.title)

        def __cleanGmailSubject(self, n):
            n = re.sub(r"^[^>]*\\>", "", n) # "sadf\>fdas" -> "fdas"
            n = re.sub(r"\\[^>]*\\>$", "", n) # "asdf\afdsasdf\>" -> "asdf"
            n = n.replace("&quot;", "\"")
            n = n.replace("&amp;", "&")
            n = n.replace("&nbsp;", "")

            if len(n) > 37:
                n = n[:37] + "..."
            elif n == "":
                n = _("[No Subject]")
            return n

        def __cleanMsg(self, n):
            n = re.sub("\n\s*\n", "\n", n)
            n = re.sub("&[#x(0x)]?\w*;", " ", n)
            n = re.sub("\<[^\<\>]*?\>", "", n) # "<h>asdf<a></h>" -> "asdf"

            f = False
            h = []
            n = n.split("\n")
            for line in n:
                if f:
                    h.append(line)
                elif re.match("X-Spam-Score", line):
                    f = True
            n = "\n".join(h)
            # Get source of message
            return n

    class GApps:
        title = _("Google Apps")

        def __init__(self, key):
            self.key = key

        def url(self):
            return "http://mail.google.com/a/%s" % self.key.attrs["username"]

        def update(self):
            f = feedparser.parse( \
                "https://%s%%40%s:%s@mail.google.com/a/%s/feed/atom" \
                 % (self.key.attrs["username"], self.key.attrs["domain"], \
                 self.key.password, self.key.attrs["domain"]))

            if "bozo_exception" in f.keys():
                raise RuntimeError, _("There seem to be problems with our \
connection to your account. Your best bet is probably \
to log out and try again.")
            # Hehe, Google is funny. Bozo exception

            t = []
            self.subjects = []
            for i in f.entries:
                i.title = self.__cleanGmailSubject(i.title)
                t.append(MailItem(i.title, i.author))
                self.subjects.append(i.title)

        def __cleanGmailSubject(self, n):
            n = re.sub(r"^[^>]*\\>", "", n) # "sadf\>fdas" -> "fdas"
            n = re.sub(r"\\[^>]*\\>$", "", n) # "asdf\afdsasdf\>" -> "asdf"
            n = n.replace("&quot;", "\"")
            n = n.replace("&amp;", "&")
            n = n.replace("&nbsp;", "")

            if len(n) > 37:
                n = n[:37] + "..."
            elif n == "":
                n = _("[No Subject]")
            return n

        def __cleanMsg(self, n):
            n = re.sub("\n\s*\n", "\n", n)
            n = re.sub("&[#x(0x)]?\w*;", " ", n)
            n = re.sub("\<[^\<\>]*?\>", "", n) # "<h>asdf<a></h>" -> "asdf"

            f = False
            h = []
            n = n.split("\n")
            for line in n:
                if f:
                    h.append(line)
                elif re.match("X-Spam-Score", line):
                    f = True
            n = "\n".join(h)
            # Get source of message
            return n

        @classmethod
        def drawLoginWindow(cls, *groups):
            vbox = gtk.VBox(spacing=12)

            usrE, box = get_label_entry(_("Username:"), *groups)
            vbox.add(box)

            pwdE, box = get_label_entry(_("Password:"), *groups)
            pwdE.set_visibility(False)
            vbox.add(box)

            domE, box = get_label_entry(_("Domain:"), *groups)
            vbox.add(box)
            
            return {"layout": vbox, "callback": cls.__submitLoginWindow,
                "widgets": [usrE, pwdE, domE]}

        @staticmethod
        def __submitLoginWindow(widgets, awn):
            return awn.keyring.new("Mail Applet - %s(%s)" \
                % (widgets[0].get_text(), "GApps"), \
                widgets[1].get_text(), \
                {"username": widgets[0].get_text(),
                "domain": widgets[2].get_text()}, "network")

#    class Empty:
#        def __init__(self, key):
#            self.subjects = [_("Dummy Message")]
#
#        def update(self):
#            pass

    try:
        global mailbox
        import mailbox
    except:
        pass
    else:
        class UnixSpool:
            title = _("Unix Spool")

            def __init__(self, key):
                self.path = key.attrs["path"]
            
            def update(self):
                self.box = mailbox.mbox(self.path)
                email = []

                self.subjects = []
                for i, msg in self.box.items():
                    if "subject" in msg:
                        subject = msg["subject"]
                    else:
                        subject = "[No Subject]"

                    self.subjects.append(subject)
            
            @classmethod
            def drawLoginWindow(cls, *groups):
                vbox = gtk.VBox(spacing=12)

                path, box = get_label_entry(_("Spool Path:"), *groups)
                vbox.add(box)

                path.set_text("/var/spool/mail/" + os.path.split(os.path.expanduser("~"))[1])

                return {"layout": vbox, "callback": cls.__submitLoginWindow,
                    "widgets": [path]}

            @staticmethod
            def __submitLoginWindow(widgets, awn):
                return awn.keyring.new("Mail Applet - %s" \
                    % "UnixSpool", "-", \
                    {"path": widgets[0].get_text(),
                     "username": os.path.split(widgets[0].get_text())[1]},
                     "network")

    try:
        global poplib
        import poplib
    except:
        pass
    else:
        class POP:
            title = "POP"

            def __init__(self, key):
                if key.attrs["usessl"]:
                    self.server = poplib.POP3_SSL(key.attrs["url"])
                else:
                    self.server = poplib.POP3(key.attrs["url"])

                self.server.user(key.attrs["username"])
                try:
                    self.server.pass_(key.password)
                except poplib.error_proto:
                    raise RuntimeError, _("Could not log in")

            def update(self):
                messagesInfo = self.server.list()[1][-20:]
                # Server messages? Too bad

                emails = []
                for msg in messagesInfo:
                    msgNum = int(msg.split(" ")[0])
                    msgSize = int(msg.split(" ")[1])
                    if msgSize < 10000:
                        message = self.server.retr(msgNum)[1]
                        message = "\n".join(message)
                        emails.append(message)

                #t = []
                self.subjects = []
                for i in emails:
                    msg = email.message_from_string(i)

                    #t.append(MailItem(i.title, i.author))
                    # TODO: Actually do something with t
                    # TODO: Implement body previews

                    if "subject" in msg:
                        subject = msg["subject"]
                    else:
                        subject = "[No Subject]"

                    self.subjects.append(subject)

            @classmethod
            def drawLoginWindow(cls, *groups):
                vbox = gtk.VBox(spacing=12)
                
                usrE, box = get_label_entry(_("Username:"), *groups)
                vbox.add(box)

                pwdE, box = get_label_entry(_("Password:"), *groups)
                pwdE.set_visibility(False)
                vbox.add(box)

                srvE, box = get_label_entry(_("Server:"), *groups)
                vbox.add(box)

                sslE = gtk.CheckButton(label=_("Use SSL encryption"))
                vbox.add(sslE)
                
                return {"layout": vbox, "callback": cls.__submitLoginWindow,
                    "widgets": [usrE, pwdE, srvE, sslE]}

            @staticmethod
            def __submitLoginWindow(widgets, awn):
                return awn.keyring.new("Mail Applet - %s(%s)" \
                    % (widgets[0].get_text(), "POP"), \
                    widgets[1].get_text(), \
                    {"username": widgets[0].get_text(),
                    "url": widgets[2].get_text(),
                    "usessl": widgets[3].get_active()}, "network")

    try:
        global imaplib
        import imaplib
    except:
        pass
    else:
        class IMAP:
            title = "IMAP"

            def __init__(self, key):
                args = key.attrs["url"].split(":")
                
                if key.attrs["usessl"]:
                    self.server = imaplib.IMAP4_SSL(*args)
                else:
                    self.server = imaplib.IMAP(*args)

                try:
                    self.server.login(key.attrs["username"], key.password)
                except poplib.error_proto:
                    raise RuntimeError, _("Could not log in")
                
                mboxs = [i.split(")")[1].split(" ", 2)[2].strip('"') for i in self.server.list()[1]]
                self.box = key.attrs["folder"]

                if self.box not in mboxs and self.box != "":
                    raise RuntimeError, _("Folder does not exst")

                if self.box != "":
                    self.server.select(self.box)

            def update(self):
                self.subjects = []

                if self.box != "":
                    emails = [i for i in self.server.search(None, "(UNSEEN)")[1][0].split(" ") if i != ""]
                    
                    for i in emails:
                        s = self.server.fetch(i, '(BODY[HEADER.FIELDS (SUBJECT)])')[1][0]
                        
                        if s is not None:
                            self.subjects.append(s[1][9:].replace("\r\n", "\n").replace("\n", "")) # Don't ask
                else:
                    mboxs = [re.search("(\W*) (\W*) (.*)", i).groups()[2][1:-1] for i in self.server.list()[1]]
                    mboxs = [i for i in mboxs if i not in ("Sent", "Trash") and i[:6] != "[Gmail]"]
                    
                    emails = []
                    for b in mboxs:
                        r, d = self.server.select(b)

                        if r == "NO":
                            continue
                        
                        p = self.server.search("UTF8", "(UNSEEN)")[1][0].split(" ")
                        
                        emails.extend([i for i in p if i != ""])
                        
                        for i in emails:
                            s = self.server.fetch(i, '(BODY[HEADER.FIELDS (SUBJECT)])')[1][0]
                            
                            if s is not None:
                                self.subjects.append(s[1][9:].replace("\r\n", "\n").replace("\n", "")) # Don't ask

            @classmethod
            def drawLoginWindow(cls, *groups):
                vbox = gtk.VBox(spacing=12)

                usrE, box = get_label_entry(_("Username:"), *groups)
                vbox.add(box)

                pwdE, box = get_label_entry(_("Password:"), *groups)
                pwdE.set_visibility(False)
                vbox.add(box)

                srvE, box = get_label_entry(_("Server:"), *groups)
                vbox.add(box)

                sslE = gtk.CheckButton(label=_("Use SSL encryption"))
                vbox.add(sslE)

                allE = gtk.CheckButton(label=_("Get messages from only one folder"))
                allE.set_active(True)
                vbox.add(allE)

                hbox_box = gtk.HBox(False, 12)
                vbox.add(hbox_box)

                foldE, boxE = get_label_entry(_("Password:"), *groups)
                foldE.set_text("INBOX")
                vbox.add(boxE)

                def on_toggle(w):
                    boxE.set_sensitive(allE.get_active())

                allE.connect("toggled", on_toggle)

                return {"layout": vbox, "callback": cls.__submitLoginWindow,
                    "widgets": [usrE, pwdE, srvE, sslE, allE, boxE]}

            @staticmethod
            def __submitLoginWindow(widgets, awn):
                if widgets[4].get_active():
                    folder = widgets[5].get_text()

                    if folder == "":
                        folder = "INBOX"
                else:
                    folder = ""
                
                return awn.keyring.new("Mail Applet - %s(%s)" \
                    % (widgets[0].get_text(), "IMAP"), \
                    widgets[1].get_text(), \
                    {"username": widgets[0].get_text(),
                    "url": widgets[2].get_text(),
                    "usessl": widgets[3].get_active(),
                    "folder": folder}, "network")

if __name__ == "__main__":
    awnlib.init_start(MailApplet, {
        "name": _("Mail Applet"),
        "short": "mail",
        "version": defs.VERSION,
        "description": _("An applet to check one's email"),
        "logo": os.path.join(os.path.dirname(__file__), "Themes/Tango/read.svg"),
        "author": "Pavel Panchekha",
        "copyright-year": "2008, 2009",
        "email": "pavpanchekha@gmail.com",
        "type": ["Network", "Email"]},
        ["settings-per-instance", "detach"])
