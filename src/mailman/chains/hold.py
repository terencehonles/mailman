# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""The terminal 'hold' chain."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'HoldChain',
    'HoldNotification',
    ]


import logging

from email.mime.message import MIMEMessage
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from mailman.app.moderator import hold_message
from mailman.app.replybot import can_acknowledge
from mailman.chains.base import ChainNotification, TerminalChainBase
from mailman.config import config
from mailman.core.i18n import _
from mailman.email.message import UserNotification
from mailman.interfaces.autorespond import IAutoResponseSet, Response
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.pending import IPendable, IPendings
from mailman.interfaces.usermanager import IUserManager
from mailman.utilities.i18n import make
from mailman.utilities.string import oneline, wrap


log = logging.getLogger('mailman.vette')
SEMISPACE = '; '



class HeldMessagePendable(dict):
    implements(IPendable)
    PEND_KEY = 'held message'


class HoldNotification(ChainNotification):
    """A notification event signaling that a message is being held."""



def autorespond_to_sender(mlist, sender, language=None):
    """Should Mailman automatically respond to this sender?

    :param mlist: The mailing list.
    :type mlist: `IMailingList`.
    :param sender: The sender's email address.
    :type sender: string
    :param language: Optional language.
    :type language: `ILanguage` or None
    :return: True if an automatic response should be sent, otherwise False.
        If an automatic response is not sent, a message is sent indicating
        that, er no more will be sent today.
    :rtype: bool
    """
    if language is None:
        language = mlist.preferred_language
    max_autoresponses_per_day = int(config.mta.max_autoresponses_per_day)
    if max_autoresponses_per_day == 0:
        # Unlimited.
        return True
    # Get an IAddress from an email address.
    user_manager = getUtility(IUserManager)
    address = user_manager.get_address(sender)
    if address is None:
        address = user_manager.create_address(sender)
    response_set = IAutoResponseSet(mlist)
    todays_count = response_set.todays_count(address, Response.hold)
    if todays_count < max_autoresponses_per_day:
        # This person has not reached their automatic response limit, so it's
        # okay to send a response.
        response_set.response_sent(address, Response.hold)
        return True
    elif todays_count == max_autoresponses_per_day:
        # The last one we sent was the last one we should send today.  Instead
        # of sending an automatic response, send them the "no more today"
        # message.
        log.info('hold autoresponse limit hit: %s', sender)
        response_set.response_sent(address, Response.hold)
        # Send this notification message instead.
        text = make('nomoretoday.txt',
                    language=language.code,
                    sender=sender,
                    listname=mlist.fqdn_listname,
                    count=todays_count,
                    owneremail=mlist.owner_address,
                    )
        with _.using(language.code):
            msg = UserNotification(
                sender, mlist.owner_address,
                _('Last autoresponse notification for today'),
                text, lang=language)
        msg.send(mlist)
        return False
    else:
        # We've sent them everything we're going to send them today.
        log.info('Automatic response limit discard: %s', sender)
        return False



class HoldChain(TerminalChainBase):
    """Hold a message."""

    name = 'hold'
    description = _('Hold a message and stop processing.')

    def _process(self, mlist, msg, msgdata):
        """See `TerminalChainBase`."""
        # Start by decorating the message with a header that contains a list
        # of all the rules that matched.  These metadata could be None or an
        # empty list.
        rule_hits = msgdata.get('rule_hits')
        if rule_hits:
            msg['X-Mailman-Rule-Hits'] = SEMISPACE.join(rule_hits)
        rule_misses = msgdata.get('rule_misses')
        if rule_misses:
            msg['X-Mailman-Rule-Misses'] = SEMISPACE.join(rule_misses)
        # Hold the message by adding it to the list's request database.
        # XXX How to calculate the reason?
        request_id = hold_message(mlist, msg, msgdata, None)
        # Calculate a confirmation token to send to the author of the
        # message.
        pendable = HeldMessagePendable(type=HeldMessagePendable.PEND_KEY,
                                       id=request_id)
        token = getUtility(IPendings).add(pendable)
        # Get the language to send the response in.  If the sender is a
        # member, then send it in the member's language, otherwise send it in
        # the mailing list's preferred language.
        member = mlist.members.get_member(msg.sender)
        language = (member.preferred_language
                    if member else mlist.preferred_language)
        # A substitution dictionary for the email templates.
        charset = mlist.preferred_language.charset
        original_subject = msg.get('subject')
        if original_subject is None:
            original_subject = _('(no subject)')
        else:
            original_subject = oneline(original_subject, charset)
        substitutions = dict(
            listname    = mlist.fqdn_listname,
            subject     = original_subject,
            sender      = msg.sender,
            reason      = 'XXX', #reason,
            confirmurl  = '{0}/{1}'.format(mlist.script_url('confirm'), token),
            admindb_url = mlist.script_url('admindb'),
            )
        # At this point the message is held, but now we have to craft at least
        # two responses.  The first will go to the original author of the
        # message and it will contain the token allowing them to approve or
        # discard the message.  The second one will go to the moderators of
        # the mailing list, if the list is so configured.
        #
        # Start by possibly sending a response to the message author.  There
        # are several reasons why we might not go through with this.  If the
        # message was gated from NNTP, the author may not even know about this
        # list, so don't spam them.  If the author specifically requested that
        # acknowledgments not be sent, or if the message was bulk email, then
        # we do not send the response.  It's also possible that either the
        # mailing list, or the author (if they are a member) have been
        # configured to not send such responses.
        if (not msgdata.get('fromusenet') and
            can_acknowledge(msg) and
            mlist.respond_to_post_requests and
            autorespond_to_sender(mlist, msg.sender, language)):
            # We can respond to the sender with a message indicating their
            # posting was held.
            subject = _(
              'Your message to $mlist.fqdn_listname awaits moderator approval')
            send_language_code = msgdata.get('lang', language.code)
            text = make('postheld.txt',
                        mailing_list=mlist,
                        language=send_language_code,
                        **substitutions)
            adminaddr = mlist.bounces_address
            nmsg = UserNotification(
                msg.sender, adminaddr, subject, text,
                getUtility(ILanguageManager)[send_language_code])
            nmsg.send(mlist)
        # Now the message for the list moderators.  This one should appear to
        # come from <list>-owner since we really don't need to do bounce
        # processing on it.
        if mlist.admin_immed_notify:
            # Now let's temporarily set the language context to that which the
            # administrators are expecting.
            with _.using(mlist.preferred_language.code):
                language = mlist.preferred_language
                charset = language.charset
                # We need to regenerate or re-translate a few values in the
                # substitution dictionary.
                #d['reason'] = _(reason) # XXX reason
                substitutions['subject'] = original_subject
                # craft the admin notification message and deliver it
                subject = _(
                    '$mlist.fqdn_listname post from $msg.sender requires '
                    'approval')
                nmsg = UserNotification(mlist.owner_address,
                                        mlist.owner_address,
                                        subject, lang=language)
                nmsg.set_type('multipart/mixed')
                text = MIMEText(make('postauth.txt',
                                     mailing_list=mlist,
                                     wrap=False,
                                     **substitutions),
                                _charset=charset)
                dmsg = MIMEText(wrap(_("""\
If you reply to this message, keeping the Subject: header intact, Mailman will
discard the held message.  Do this if the message is spam.  If you reply to
this message and include an Approved: header with the list password in it, the
message will be approved for posting to the list.  The Approved: header can
also appear in the first line of the body of the reply.""")),
                                _charset=language.charset)
                dmsg['Subject'] = 'confirm ' + token
                dmsg['From'] = mlist.request_address
                dmsg['Date'] = formatdate(localtime=True)
                dmsg['Message-ID'] = make_msgid()
                nmsg.attach(text)
                nmsg.attach(MIMEMessage(msg))
                nmsg.attach(MIMEMessage(dmsg))
                nmsg.send(mlist, **dict(tomoderators=True))
        # Log the held message
        # XXX reason
        reason = 'n/a'
        log.info('HOLD: %s post from %s held, message-id=%s: %s',
                 mlist.fqdn_listname, msg.sender,
                 msg.get('message-id', 'n/a'), reason)
        notify(HoldNotification(mlist, msg, msgdata, self))
