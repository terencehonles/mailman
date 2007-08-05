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

"""Handle delivery bounces."""

import sys
import time
import logging

from email.MIMEMessage import MIMEMessage
from email.MIMEText import MIMEText

from Mailman import Defaults
from Mailman import MemberAdaptor
from Mailman import Message
from Mailman import Utils
from Mailman import i18n
from Mailman.configuration import config

EMPTYSTRING = ''

# This constant is supposed to represent the day containing the first midnight
# after the epoch.  We'll add (0,)*6 to this tuple to get a value appropriate
# for time.mktime().
ZEROHOUR_PLUSONEDAY = time.localtime(60 * 60 * 24)[:3]

def _(s): return s

REASONS = {MemberAdaptor.BYBOUNCE: _('due to excessive bounces'),
           MemberAdaptor.BYUSER: _('by yourself'),
           MemberAdaptor.BYADMIN: _('by the list administrator'),
           MemberAdaptor.UNKNOWN: _('for unknown reasons'),
           }

_ = i18n._

log     = logging.getLogger('mailman.bounce')
slog    = logging.getLogger('mailman.subscribe')



class _BounceInfo:
    def __init__(self, member, score, date, noticesleft):
        self.member = member
        self.cookie = None
        self.reset(score, date, noticesleft)

    def reset(self, score, date, noticesleft):
        self.score = score
        self.date = date
        self.noticesleft = noticesleft
        self.lastnotice = ZEROHOUR_PLUSONEDAY

    def __repr__(self):
        # For debugging
        return """\
<bounce info for member %(member)s
        current score: %(score)s
        last bounce date: %(date)s
        email notices left: %(noticesleft)s
        last notice date: %(lastnotice)s
        confirmation cookie: %(cookie)s
        >""" % self.__dict__



class Bouncer:
    def registerBounce(self, member, msg, weight=1.0, day=None):
        if not self.isMember(member):
            return
        info = self.getBounceInfo(member)
        if day is None:
            # Use today's date
            day = time.localtime()[:3]
        if not isinstance(info, _BounceInfo):
            # This is the first bounce we've seen from this member
            info = _BounceInfo(member, weight, day,
                               self.bounce_you_are_disabled_warnings)
            self.setBounceInfo(member, info)
            log.info('%s: %s bounce score: %s', self.internal_name(),
                     member, info.score)
            # Continue to the check phase below
        elif self.getDeliveryStatus(member) <> MemberAdaptor.ENABLED:
            # The user is already disabled, so we can just ignore subsequent
            # bounces.  These are likely due to residual messages that were
            # sent before disabling the member, but took a while to bounce.
            log.info('%s: %s residual bounce received',
                     self.internal_name(), member)
            return
        elif info.date == day:
            # We've already scored any bounces for this day, so ignore it.
            log.info('%s: %s already scored a bounce for date %s',
                     self.internal_name(), member,
                     time.strftime('%d-%b-%Y', day + (0,0,0,0,1,0)))
            # Continue to check phase below
        else:
            # See if this member's bounce information is stale.
            now = Utils.midnight(day)
            lastbounce = Utils.midnight(info.date)
            if lastbounce + self.bounce_info_stale_after < now:
                # Information is stale, so simply reset it
                info.reset(weight, day, self.bounce_you_are_disabled_warnings)
                log.info('%s: %s has stale bounce info, resetting',
                         self.internal_name(), member)
            else:
                # Nope, the information isn't stale, so add to the bounce
                # score and take any necessary action.
                info.score += weight
                info.date = day
                log.info('%s: %s current bounce score: %s',
                         self.internal_name(), member, info.score)
            # Continue to the check phase below
        #
        # Now that we've adjusted the bounce score for this bounce, let's
        # check to see if the disable-by-bounce threshold has been reached.
        if info.score >= self.bounce_score_threshold:
            if config.VERP_PROBES:
                log.info('sending %s list probe to: %s (score %s >= %s)',
                         self.internal_name(), member, info.score,
                         self.bounce_score_threshold)
                self.sendProbe(member, msg)
                info.reset(0, info.date, info.noticesleft)
            else:
                self.disableBouncingMember(member, info, msg)

    def disableBouncingMember(self, member, info, msg):
        # Initialize their confirmation cookie.  If we do it when we get the
        # first bounce, it'll expire by the time we get the disabling bounce.
        cookie = self.pend_new(Pending.RE_ENABLE, self.internal_name(), member)
        info.cookie = cookie
        # Disable them
        if config.VERP_PROBES:
            log.info('%s: %s disabling due to probe bounce received',
                     self.internal_name(), member)
        else:
            log.info('%s: %s disabling due to bounce score %s >= %s',
                     self.internal_name(), member,
                     info.score, self.bounce_score_threshold)
        self.setDeliveryStatus(member, MemberAdaptor.BYBOUNCE)
        self.sendNextNotification(member)
        if self.bounce_notify_owner_on_disable:
            self.__sendAdminBounceNotice(member, msg)

    def __sendAdminBounceNotice(self, member, msg):
        # BAW: This is a bit kludgey, but we're not providing as much
        # information in the new admin bounce notices as we used to (some of
        # it was of dubious value).  However, we'll provide empty, strange, or
        # meaningless strings for the unused %()s fields so that the language
        # translators don't have to provide new templates.
        text = Utils.maketext(
            'bounce.txt',
            {'listname' : self.real_name,
             'addr'     : member,
             'negative' : '',
             'did'      : _('disabled'),
             'but'      : '',
             'reenable' : '',
             'owneraddr': self.no_reply_address,
             }, mlist=self)
        subject = _('Bounce action notification')
        umsg = Message.UserNotification(self.GetOwnerEmail(),
                                        self.no_reply_address,
                                        subject,
                                        lang=self.preferred_language)
        # BAW: Be sure you set the type before trying to attach, or you'll get
        # a MultipartConversionError.
        umsg.set_type('multipart/mixed')
        umsg.attach(
            MIMEText(text, _charset=Utils.GetCharSet(self.preferred_language)))
        if isinstance(msg, str):
            umsg.attach(MIMEText(msg))
        else:
            umsg.attach(MIMEMessage(msg))
        umsg.send(self)

    def sendNextNotification(self, member):
        info = self.getBounceInfo(member)
        if info is None:
            return
        reason = self.getDeliveryStatus(member)
        if info.noticesleft <= 0:
            # BAW: Remove them now, with a notification message
            self.ApprovedDeleteMember(
                member, 'disabled address',
                admin_notif=self.bounce_notify_owner_on_removal,
                userack=1)
            # Expunge the pending cookie for the user.  We throw away the
            # returned data.
            self.pend_confirm(info.cookie)
            if reason == MemberAdaptor.BYBOUNCE:
                log.info('%s: %s deleted after exhausting notices',
                         self.internal_name(), member)
            slog.info('%s: %s auto-unsubscribed [reason: %s]',
                      self.internal_name(), member,
                      {MemberAdaptor.BYBOUNCE: 'BYBOUNCE',
                       MemberAdaptor.BYUSER: 'BYUSER',
                       MemberAdaptor.BYADMIN: 'BYADMIN',
                       MemberAdaptor.UNKNOWN: 'UNKNOWN'}.get(
                reason, 'invalid value'))
            return
        # Send the next notification
        confirmurl = '%s/%s' % (self.GetScriptURL('confirm', absolute=1),
                                info.cookie)
        optionsurl = self.GetOptionsURL(member, absolute=1)
        reqaddr = self.GetRequestEmail()
        lang = self.getMemberLanguage(member)
        txtreason = REASONS.get(reason)
        if txtreason is None:
            txtreason = _('for unknown reasons')
        else:
            txtreason = _(txtreason)
        # Give a little bit more detail on bounce disables
        if reason == MemberAdaptor.BYBOUNCE:
            date = time.strftime('%d-%b-%Y',
                                 time.localtime(Utils.midnight(info.date)))
            extra = _(' The last bounce received from you was dated %(date)s')
            txtreason += extra
        text = Utils.maketext(
            'disabled.txt',
            {'listname'   : self.real_name,
             'noticesleft': info.noticesleft,
             'confirmurl' : confirmurl,
             'optionsurl' : optionsurl,
             'password'   : self.getMemberPassword(member),
             'owneraddr'  : self.GetOwnerEmail(),
             'reason'     : txtreason,
             }, lang=lang, mlist=self)
        msg = Message.UserNotification(member, reqaddr, text=text, lang=lang)
        # BAW: See the comment in MailList.py ChangeMemberAddress() for why we
        # set the Subject this way.
        del msg['subject']
        msg['Subject'] = 'confirm ' + info.cookie
        msg.send(self)
        info.noticesleft -= 1
        info.lastnotice = time.localtime()[:3]

    def bounce_message(self, msg, e=None):
        # Bounce a message back to the sender, with an error message if
        # provided in the exception argument.
        sender = msg.get_sender()
        subject = msg.get('subject', _('(no subject)'))
        subject = Utils.oneline(subject,
                                Utils.GetCharSet(self.preferred_language))
        if e is None:
            notice = _('[No bounce details are available]')
        else:
            notice = _(e.notice)
        # Currently we always craft bounces as MIME messages.
        bmsg = Message.UserNotification(msg.get_sender(),
                                        self.owner_address,
                                        subject,
                                        lang=self.preferred_language)
        # BAW: Be sure you set the type before trying to attach, or you'll get
        # a MultipartConversionError.
        bmsg.set_type('multipart/mixed')
        txt = MIMEText(notice,
                       _charset=Utils.GetCharSet(self.preferred_language))
        bmsg.attach(txt)
        bmsg.attach(MIMEMessage(msg))
        bmsg.send(self)
