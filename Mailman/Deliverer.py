# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software 
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


"""Mixin class with message delivery routines."""

import os

from Mailman import mm_cfg
from Mailman import Errors
from Mailman import Utils
from Mailman import Message
from Mailman.i18n import _
from Mailman.Logging.Syslog import syslog



class Deliverer:
    def SendSubscribeAck(self, name, password, digest):
        pluser = self.getMemberLanguage(name)
        if not self.send_welcome_msg:
	    return
	if self.welcome_msg:
	    welcome = Utils.wrap(self.welcome_msg) + '\n'
	else:
	    welcome = ''
        if self.umbrella_list:
            addr = self.GetMemberAdminEmail(name)
            umbrella = Utils.wrap(_('''\
Note: Since this is a list of mailing lists, administrative
notices like the password reminder will be sent to
your membership administrative address, %(addr)s.'''))
        else:
            umbrella = ''
        # get the text from the template
        text = Utils.maketext(
            'subscribeack.txt',
            {'real_name'   : self.real_name,
             'host_name'   : self.host_name,
             'welcome'     : welcome,
             'umbrella'    : umbrella,
             'emailaddr'   : self.GetListEmail(),
             'listinfo_url': self.GetScriptURL('listinfo', absolute=1),
             'optionsurl'  : self.GetOptionsURL(name, absolute=1),
             'password'    : password,
             }, lang=pluser, mlist=self)
	if digest:
	    digmode = _(' (Digest mode)')
	else:
	    digmode = ''
        realname = self.real_name
        msg = Message.UserNotification(
            self.GetMemberAdminEmail(name), self.GetRequestEmail(),
            _('Welcome to the "%(realname)s" mailing list%(digmode)s'),
            text)
        msg['X-No-Archive'] = 'yes'
        msg.send(self)

    def SendUnsubscribeAck(self, name):
        realname = self.real_name
        msg = Message.UserNotification(
            self.GetMemberAdminEmail(name), self.GetAdminEmail(),
            _('Unsubscribed from "%(realname)s" mailing list'),
            Utils.wrap(self.goodbye_msg))
        msg.send(self)

    def MailUserPassword(self, user):
        listfullname = '%s@%s' % (self.real_name, self.host_name)
        requestaddr = self.GetRequestEmail()
        # find the lowercased version of the user's address
        adminaddr = self.GetAdminEmail()
        assert self.isMember(user)
        if not self.getMemberPassword(user):
            # The user's password somehow got corrupted.  Generate a new one
            # for him, after logging this bogosity.
            syslog('error', 'User %s had a false password for list %s',
                   user, self.internal_name())
            waslocked = self.Locked()
            if not waslocked:
                self.Lock()
            try:
                self.setMemberPassword(user, Utils.MakeRandomPassword())
                self.Save()
            finally:
                if not waslocked:
                    self.Unlock()
        # Now send the user his password
        cpuser = self.getMemberCPAddress(user)
        recipient = self.GetMemberAdminEmail(cpuser)
        subject = _('%(listfullname)s mailing list reminder')
        # get the text from the template
        text = Utils.maketext(
            'userpass.txt',
            {'user'       : cpuser,
             'listname'   : self.real_name,
             'fqdn_lname' : self.GetListEmail(),
             'password'   : self.passwords[user],
             'options_url': self.GetOptionsURL(user, absolute=1),
             'requestaddr': requestaddr,
             'owneraddr'  : self.GetOwnerEmail(),
            }, lang=self.getMemberLanguage(user), mlist=self)
        msg = Message.UserNotification(recipient, adminaddr, subject, text)
        msg['X-No-Archive'] = 'yes'
        msg.send(self)
