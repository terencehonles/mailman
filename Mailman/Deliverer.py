# Copyright (C) 1998-2007 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.


"""Mixin class with message delivery routines."""

import logging

from email.MIMEMessage import MIMEMessage
from email.MIMEText import MIMEText

from Mailman import Errors
from Mailman import Message
from Mailman import Utils
from Mailman import i18n
from Mailman.configuration import config

_ = i18n._

log     = logging.getLogger('mailman.error')
mlog    = logging.getLogger('mailman.mischief')



class Deliverer:
    def MailUserPassword(self, user):
        listfullname = self.fqdn_listname
        requestaddr = self.GetRequestEmail()
        # find the lowercased version of the user's address
        adminaddr = self.GetBouncesEmail()
        assert self.isMember(user)
        if not self.getMemberPassword(user):
            # The user's password somehow got corrupted.  Generate a new one
            # for him, after logging this bogosity.
            log.error('User %s had a false password for list %s',
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
        # Get user's language and charset
        lang = self.getMemberLanguage(user)
        cset = Utils.GetCharSet(lang)
        password = self.getMemberPassword(user)
        # TK: Make unprintables to ?
        # The list owner should allow users to set language options if they
        # want to use non-us-ascii characters in password and send it back.
        password = unicode(password, cset, 'replace').encode(cset, 'replace')
        # get the text from the template
        text = Utils.maketext(
            'userpass.txt',
            {'user'       : cpuser,
             'listname'   : self.real_name,
             'fqdn_lname' : self.GetListEmail(),
             'password'   : password,
             'options_url': self.GetOptionsURL(user, absolute=True),
             'requestaddr': requestaddr,
             'owneraddr'  : self.GetOwnerEmail(),
            }, lang=lang, mlist=self)
        msg = Message.UserNotification(recipient, adminaddr, subject, text,
                                       lang)
        msg['X-No-Archive'] = 'yes'
        msg.send(self, verp=config.VERP_PERSONALIZED_DELIVERIES)

    def ForwardMessage(self, msg, text=None, subject=None, tomoderators=True):
        # Wrap the message as an attachment
        if text is None:
            text = _('No reason given')
        if subject is None:
            text = _('(no subject)')
        text = MIMEText(Utils.wrap(text),
                        _charset=Utils.GetCharSet(self.preferred_language))
        attachment = MIMEMessage(msg)
        notice = Message.OwnerNotification(
            self, subject, tomoderators=tomoderators)
        # Make it look like the message is going to the -owner address
        notice.set_type('multipart/mixed')
        notice.attach(text)
        notice.attach(attachment)
        notice.send(self)

    def SendHostileSubscriptionNotice(self, listname, address):
        # Some one was invited to one list but tried to confirm to a different
        # list.  We inform both list owners of the bogosity, but be careful
        # not to reveal too much information.
        selfname = self.internal_name()
        mlog.error('%s was invited to %s but confirmed to %s',
                   address, listname, selfname)
        # First send a notice to the attacked list
        msg = Message.OwnerNotification(
            self,
            _('Hostile subscription attempt detected'),
            Utils.wrap(_("""%(address)s was invited to a different mailing
list, but in a deliberate malicious attempt they tried to confirm the
invitation to your list.  We just thought you'd like to know.  No further
action by you is required.""")))
        msg.send(self)
        # Now send a notice to the invitee list
        try:
            # Avoid import loops
            from Mailman.MailList import MailList
            mlist = MailList(listname, lock=False)
        except Errors.MMListError:
            # Oh well
            return
        otrans = i18n.get_translation()
        i18n.set_language(mlist.preferred_language)
        try:
            msg = Message.OwnerNotification(
                mlist,
                _('Hostile subscription attempt detected'),
                Utils.wrap(_("""You invited %(address)s to your list, but in a
deliberate malicious attempt, they tried to confirm the invitation to a
different list.  We just thought you'd like to know.  No further action by you
is required.""")))
            msg.send(mlist)
        finally:
            i18n.set_translation(otrans)

    def sendProbe(self, member, msg):
        listname = self.real_name
        # Put together the substitution dictionary.
        d = {'listname': listname,
             'address': member,
             'optionsurl': self.GetOptionsURL(member, absolute=True),
             'owneraddr': self.GetOwnerEmail(),
             }
        text = Utils.maketext('probe.txt', d,
                              lang=self.getMemberLanguage(member),
                              mlist=self)
        # Calculate the VERP'd sender address for bounce processing of the
        # probe message.
        token = self.pend_new(Pending.PROBE_BOUNCE, member, msg)
        probedict = {
            'bounces': self.internal_name() + '-bounces',
            'token': token,
            }
        probeaddr = '%s@%s' % ((config.VERP_PROBE_FORMAT % probedict),
                               self.host_name)
        # Calculate the Subject header, in the member's preferred language
        ulang = self.getMemberLanguage(member)
        otrans = i18n.get_translation()
        i18n.set_language(ulang)
        try:
            subject = _('%(listname)s mailing list probe message')
        finally:
            i18n.set_translation(otrans)
        outer = Message.UserNotification(member, probeaddr, subject,
                                         lang=ulang)
        outer.set_type('multipart/mixed')
        text = MIMEText(text, _charset=Utils.GetCharSet(ulang))
        outer.attach(text)
        outer.attach(MIMEMessage(msg))
        # Turn off further VERP'ing in the final delivery step.  We set
        # probe_token for the OutgoingRunner to more easily handling local
        # rejects of probe messages.
        outer.send(self, envsender=probeaddr, verp=False, probe_token=token)
