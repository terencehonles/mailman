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



class Deliverer:
    def SendSubscribeAck(self, name, password, digest):
        pluser = self.GetPreferredLanguage(name)
        os.environ['LANG'] = pluser
        if not self.send_welcome_msg:
	    return
	if self.welcome_msg:
	    welcome = Utils.wrap(self.welcome_msg) + '\n'
	else:
	    welcome = ''
        if self.umbrella_list:
            umbrella = Utils.wrap(_('''\
Note: Since this is a list of mailing lists, administrative
notices like the password reminder will be sent to
your membership administrative address, %s.
''') % self.GetMemberAdminEmail(name))
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
             }, pluser) 
	if digest:
	    digmode = _(" (Digest mode)")
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
        os.environ['LANG'] = self.GetPreferredLanguage(name)
        msg = Message.UserNotification(
            self.GetMemberAdminEmail(name), self.GetAdminEmail(),
            _('Unsubscribed from "%s" mailing list') % self.real_name,
            Utils.wrap(self.goodbye_msg))
        msg.send(self)

    def MailUserPassword(self, user):
        os.environ['LANG'] = self.GetPreferredLanguage(user)
        listfullname = '%s@%s' % (self.real_name, self.host_name)
        ok = 1
        # find the lowercased version of the user's address
        user = self.FindUser(user)
        requestaddr = self.GetRequestEmail()
        if user and self.passwords.has_key(user):
            cpuser = self.GetUserSubscribedAddress(user)
            recipient = self.GetMemberAdminEmail(cpuser)
            subject = _('%s mailing list reminder') % listfullname
            adminaddr = self.GetAdminEmail()
            # get the text from the template
            text = Utils.maketext(
                'userpass.txt',
                {'user'       : cpuser,
                 'listname'   : self.real_name,
                 'password'   : self.passwords[user],
                 'options_url': self.GetOptionsURL(user, absolute=1),
                 'requestaddr': requestaddr,
                 'adminaddr'  : adminaddr,
                }, self.GetPreferredLanguage(user))
        else:
            ok = 0
            recipient = self.GetAdminEmail()
            subject = _('%s user %s missing password!') % (listfullname, user)
            text = Utils.maketext(
                'nopass.txt',
                {'username'     : `user`,
                 'internal_name': self.internal_name(),
                 }, self.GetPreferredLanguage(user))
        msg = Message.UserNotification(recipient, requestaddr, subject, text)
        msg['X-No-Archive'] = 'yes'
        msg.send(self)
        if not ok:
             raise Errors.MMBadUserError
