# Copyright (C) 1998 by the Free Software Foundation, Inc.
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
import string

from Mailman import mm_cfg
from Mailman import Errors
from Mailman import Utils
from Mailman import Message
from Mailman.Handlers import HandlerAPI



class Deliverer:
    def SendSubscribeAck(self, name, password, digest):
        if not self.send_welcome_msg:
	    return
	if self.welcome_msg:
	    welcome = Utils.wrap(self.welcome_msg) + '\n'
	else:
	    welcome = ''
        if self.umbrella_list:
            umbrella = Utils.wrap('''\
Note: Since this is a list of mailing lists, administrative
notices like the password reminder will be sent to
your membership administrative address, %s.
''' % self.GetMemberAdminEmail(name))
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
             'listinfo_url': self.GetAbsoluteScriptURL('listinfo'),
             'optionsurl'  : self.GetAbsoluteOptionsURL(name),
             'password'    : password,
             })
	if digest:
	    digmode = ' (Digest mode)'
	else:
	    digmode = ''
        msg = Message.UserNotification(
            self.GetMemberAdminEmail(name), self.GetAdminEmail(),
            'Welcome to the "%s" mailing list%s' % (self.real_name, digmode),
            text)
        HandlerAPI.DeliverToUser(self, msg)


    def SendUnsubscribeAck(self, name):
        msg = Message.UserNotification(
            self.GetMemberAdminEmail(name), self.GetAdminEmail(),
            'Unsubscribed from "%s" mailing list' % self.real_name,
            Utils.wrap(self.goodbye_msg))
        HandlerAPI.DeliverToUser(self, msg)


    def MailUserPassword(self, user):
        listfullname = '%s@%s' % (self.real_name, self.host_name)
        ok = 1
        # find the lowercased version of the user's address
        user = self.FindUser(user)
        if user and self.passwords.has_key(user):
            cpuser = self.GetUserSubscribedAddress(user)
            recipient = self.GetMemberAdminEmail(cpuser)
            subject = '%s mailing list reminder' % listfullname
            adminaddr = self.GetAdminEmail()
            # get the text from the template
            text = Utils.maketext(
                'userpass.txt',
                {'user'       : cpuser,
                 'listname'   : self.real_name,
                 'password'   : self.passwords[user],
                 'options_url': self.GetAbsoluteOptionsURL(user),
                 'requestaddr': self.GetRequestEmail(),
                 'adminaddr'  : adminaddr,
                 })
        else:
            ok = 0
            recipient = self.GetAdminEmail()
            subject = '%s user %s missing password!' % (listfullname, user)
            text = Utils.maketext(
                'nopass.txt',
                {'username'     : `user`,
                 'internal_name': self.internal_name(),
                 })
        msg = Message.UserNotification(recipient, adminaddr, subject, text)
        msg['X-No-Archive'] = 'yes'
        fp = open('/tmp/msg', 'w')
        fp.write(str(msg))
        fp.close()
        HandlerAPI.DeliverToUser(self, msg)
        if not ok:
             raise Errors.MMBadUserError
