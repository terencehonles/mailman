# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

"""The built-in rule chains."""

from __future__ import with_statement

__all__ = [
    'AcceptChain',
    'Chain',
    'DiscardChain',
    'HoldChain',
    'Link',
    'RejectChain',
    'initialize',
    'process',
    ]
__metaclass__ = type
__i18n_templates__ = True


import re
import logging

from email.mime.message import MIMEMessage
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from zope.interface import implements

from Mailman import i18n
from Mailman.Message import UserNotification
from Mailman.Utils import maketext, oneline, wrap, GetCharSet
from Mailman.app.bounces import bounce_message
from Mailman.app.moderator import hold_message
from Mailman.app.replybot import autorespond_to_sender, can_acknowledge
from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.interfaces import (
    IChain, IChainLink, IMutableChain, IPendable, IRule, LinkAction)
from Mailman.queue import Switchboard

log = logging.getLogger('mailman.vette')
elog = logging.getLogger('mailman.error')
SEMISPACE = '; '



class HeldMessagePendable(dict):
    implements(IPendable)
    PEND_KEY = 'held message'



class Link:
    """A chain link."""
    implements(IChainLink)

    def __init__(self, rule, action=None, chain=None, function=None):
        self.rule = rule
        self.action = (LinkAction.defer if action is None else action)
        self.chain = chain
        self.function = function



class TerminalChainBase:
    """A base chain that always matches and executes a method.

    The method is called 'process' and must be provided by the subclass.
    """
    implements(IChain)

    def __iter__(self):
        """See `IChain`."""
        # First, yield a link that always runs the process method.
        yield Link('truth', LinkAction.run, function=self.process)
        # Now yield a rule that stops all processing.
        yield Link('truth', LinkAction.stop)

    def process(self, mlist, msg, msgdata):
        """Process the message for the given mailing list.

        This must be overridden by subclasses.
        """
        raise NotImplementedError

    def get_rule(self, name):
        """See `IChain`.

        This always returns the globally registered named rule.
        """
        return config.rules[name]


class DiscardChain(TerminalChainBase):
    """Discard a message."""
    implements(IChain)

    name = 'discard'
    description = _('Discard a message and stop processing.')

    def process(self, mlist, msg, msgdata):
        """See `IChain`."""
        log.info('DISCARD: %s', msg.get('message-id', 'n/a'))
        # Nothing more needs to happen.



class HoldChain(TerminalChainBase):
    """Hold a message."""
    implements(IChain)

    name = 'hold'
    description = _('Hold a message and stop processing.')

    def process(self, mlist, msg, msgdata):
        """See `IChain`."""
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
        token = config.db.pendings.add(pendable)
        # Get the language to send the response in.  If the sender is a
        # member, then send it in the member's language, otherwise send it in
        # the mailing list's preferred language.
        sender = msg.get_sender()
        member = mlist.members.get_member(sender)
        language = (member.preferred_language
                    if member else mlist.preferred_language)
        # A substitution dictionary for the email templates.
        charset = GetCharSet(mlist.preferred_language)
        original_subject = msg.get('subject')
        if original_subject is None:
            original_subject = _('(no subject)')
        else:
            original_subject = oneline(original_subject, charset)
        substitutions = {
            'listname'   : mlist.fqdn_listname,
            'subject'    : original_subject,
            'sender'     : sender,
            'reason'     : 'XXX', #reason,
            'confirmurl' : '%s/%s' % (mlist.script_url('confirm'), token),
            'admindb_url': mlist.script_url('admindb'),
            }
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
            autorespond_to_sender(mlist, sender, language)):
            # We can respond to the sender with a message indicating their
            # posting was held.
            subject = _(
              'Your message to $mlist.fqdn_listname awaits moderator approval')
            send_language = msgdata.get('lang', language)
            text = maketext('postheld.txt', substitutions,
                            lang=send_language, mlist=mlist)
            adminaddr = mlist.bounces_address
            nmsg = UserNotification(sender, adminaddr, subject, text,
                                    send_language)
            nmsg.send(mlist)
        # Now the message for the list moderators.  This one should appear to
        # come from <list>-owner since we really don't need to do bounce
        # processing on it.
        if mlist.admin_immed_notify:
            # Now let's temporarily set the language context to that which the
            # administrators are expecting.
            with i18n.using_language(mlist.preferred_language):
                language = mlist.preferred_language
                charset = GetCharSet(language)
                # We need to regenerate or re-translate a few values in the
                # substitution dictionary.
                #d['reason'] = _(reason) # XXX reason
                substitutions['subject'] = original_subject
                # craft the admin notification message and deliver it
                subject = _(
                    '$mlist.fqdn_listname post from $sender requires approval')
                nmsg = UserNotification(mlist.owner_address,
                                        mlist.owner_address,
                                        subject, lang=language)
                nmsg.set_type('multipart/mixed')
                text = MIMEText(
                    maketext('postauth.txt', substitutions,
                             raw=True, mlist=mlist),
                    _charset=charset)
                dmsg = MIMEText(wrap(_("""\
If you reply to this message, keeping the Subject: header intact, Mailman will
discard the held message.  Do this if the message is spam.  If you reply to
this message and include an Approved: header with the list password in it, the
message will be approved for posting to the list.  The Approved: header can
also appear in the first line of the body of the reply.""")),
                                _charset=GetCharSet(language))
                dmsg['Subject'] = 'confirm ' + token
                dmsg['Sender'] = mlist.request_address
                dmsg['From'] = mlist.request_address
                dmsg['Date'] = formatdate(localtime=True)
                dmsg['Message-ID'] = make_msgid()
                nmsg.attach(text)
                nmsg.attach(MIMEMessage(msg))
                nmsg.attach(MIMEMessage(dmsg))
                nmsg.send(mlist, **{'tomoderators': 1})
        # Log the held message
        # XXX reason
        reason = 'n/a'
        log.info('HOLD: %s post from %s held, message-id=%s: %s',
                 mlist.fqdn_listname, sender,
                 msg.get('message-id', 'n/a'), reason)



class RejectChain(TerminalChainBase):
    """Reject/bounce a message."""
    implements(IChain)

    name = 'reject'
    description = _('Reject/bounce a message and stop processing.')

    def process(self, mlist, msg, msgdata):
        """See `IChain`."""
        # Start by decorating the message with a header that contains a list
        # of all the rules that matched.  These metadata could be None or an
        # empty list.
        rule_hits = msgdata.get('rule_hits')
        if rule_hits:
            msg['X-Mailman-Rule-Hits'] = SEMISPACE.join(rule_hits)
        rule_misses = msgdata.get('rule_misses')
        if rule_misses:
            msg['X-Mailman-Rule-Misses'] = SEMISPACE.join(rule_misses)
        # XXX Exception/reason
        bounce_message(mlist, msg)
        log.info('REJECT: %s', msg.get('message-id', 'n/a'))



class AcceptChain(TerminalChainBase):
    """Accept the message for posting."""
    implements(IChain)

    name = 'accept'
    description = _('Accept a message.')

    def process(self, mlist, msg, msgdata):
        """See `IChain.`"""
        # Start by decorating the message with a header that contains a list
        # of all the rules that matched.  These metadata could be None or an
        # empty list.
        rule_hits = msgdata.get('rule_hits')
        if rule_hits:
            msg['X-Mailman-Rule-Hits'] = SEMISPACE.join(rule_hits)
        rule_misses = msgdata.get('rule_misses')
        if rule_misses:
            msg['X-Mailman-Rule-Misses'] = SEMISPACE.join(rule_misses)
        accept_queue = Switchboard(config.PREPQUEUE_DIR)
        accept_queue.enqueue(msg, msgdata)
        log.info('ACCEPT: %s', msg.get('message-id', 'n/a'))



class Chain:
    """Generic chain base class."""
    implements(IMutableChain)

    def __init__(self, name, description):
        assert name not in config.chains, 'Duplicate chain name: %s' % name
        self.name = name
        self.description = description
        self._links = []
        # Register the chain.
        config.chains[name] = self

    def append_link(self, link):
        """See `IMutableChain`."""
        self._links.append(link)

    def flush(self):
        """See `IMutableChain`."""
        self._links = []

    def __iter__(self):
        """See `IChain`."""
        for link in self._links:
            yield link

    def get_rule(self, name):
        """See `IChain`.

        This always returns the globally registered named rule.
        """
        return config.rules[name]



class BuiltInChain(Chain):
    """Default built-in chain."""

    def __init__(self):
        super(BuiltInChain, self).__init__(
            'built-in', _('The built-in moderation chain.'))
        self.append_link(Link('approved', LinkAction.jump, 'accept'))
        self.append_link(Link('emergency', LinkAction.jump, 'hold'))
        self.append_link(Link('loop', LinkAction.jump, 'discard'))
        # Do all of the following before deciding whether to hold the message
        # for moderation.
        self.append_link(Link('administrivia', LinkAction.defer))
        self.append_link(Link('implicit-dest', LinkAction.defer))
        self.append_link(Link('max-recipients', LinkAction.defer))
        self.append_link(Link('max-size', LinkAction.defer))
        self.append_link(Link('news-moderation', LinkAction.defer))
        self.append_link(Link('no-subject', LinkAction.defer))
        self.append_link(Link('suspicious-header', LinkAction.defer))
        # Now if any of the above hit, jump to the hold chain.
        self.append_link(Link('any', LinkAction.jump, 'hold'))
        # Take a detour through the self header matching chain, which we'll
        # create later.
        self.append_link(Link('truth', LinkAction.detour, 'header-match'))
        # Finally, the builtin chain selfs to acceptance.
        self.append_link(Link('truth', LinkAction.jump, 'accept'))



class HeaderMatchRule:
    """Header matching rule used by header-match chain."""
    implements(IRule)

    # Sequential rule counter.
    _count = 1

    def __init__(self, header, pattern):
        self._header = header
        self._pattern = pattern
        self.name = 'header-match-%002d' % HeaderMatchRule._count
        HeaderMatchRule._count += 1
        self.description = u'%s: %s' % (header, pattern)
        # XXX I think we should do better here, somehow recording that a
        # particular header matched a particular pattern, but that gets ugly
        # with RFC 2822 headers.  It also doesn't match well with the rule
        # name concept.  For now, we just record the rather useless numeric
        # rule name.  I suppose we could do the better hit recording in the
        # check() method, and set self.record = False.
        self.record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        for value in msg.get_all(self._header, []):
            if re.search(self._pattern, value, re.IGNORECASE):
                return True
        return False


class HeaderMatchChain(Chain):
    """Default header matching chain.

    This could be extended by header match rules in the database.
    """

    def __init__(self):
        super(HeaderMatchChain, self).__init__(
            'header-match', _('The built-in header matching chain'))
        # The header match rules are not global, so don't register them.
        # These are the only rules that the header match chain can execute.
        self._links = []
        self._rules = {}
        # Initialize header check rules with those from the global
        # HEADER_MATCHES variable.
        for entry in config.HEADER_MATCHES:
            if len(entry) == 2:
                header, pattern = entry
                chain = 'hold'
            elif len(entry) == 3:
                header, pattern, chain = entry
                # We don't assert that the chain exists here because the jump
                # chain may not yet have been created.
            else:
                raise AssertionError(
                    'Bad entry for HEADER_MATCHES: %s' % entry)
            self.extend(header, pattern, chain)

    def extend(self, header, pattern, chain='hold'):
        """Extend the existing header matches.

        :param header: The case-insensitive header field name.
        :param pattern: The pattern to match the header's value again.  The
            match is not anchored and is done case-insensitively.
        :param chain: Option chain to jump to if the pattern matches any of
            the named header values.  If not given, the 'hold' chain is used.
        """
        rule = HeaderMatchRule(header, pattern)
        self._rules[rule.name] = rule
        link = Link(rule.name, LinkAction.jump, chain)
        self._links.append(link)

    def get_rule(self, name):
        """See `IChain`.

        Only local rules are findable by this chain.
        """
        return self._rules[name]



def process(mlist, msg, msgdata, start_chain='built-in'):
    """Process the message through a chain.

    :param start_chain: The name of the chain to start the processing with.
    :param mlist: the IMailingList for this message.
    :param msg: The Message object.
    :param msgdata: The message metadata dictionary.
    """
    # Set up some bookkeeping.
    chain_stack = []
    msgdata['rule_hits'] = hits = []
    msgdata['rule_misses'] = misses = []
    # Find the starting chain and begin iterating through its links.
    chain = config.chains[start_chain]
    chain_iter = iter(chain)
    # Loop until we've reached the end of all processing chains.
    while chain:
        # Iterate over all links in the chain.  Do this outside a for-loop so
        # we can capture a chain's link iterator in mid-flight.  This supports
        # the 'detour' link action
        try:
            link = chain_iter.next()
        except StopIteration:
            # This chain is exhausted.  Pop the last chain on the stack and
            # continue iterating through it.  If there's nothing left on the
            # chain stack then we're completely finished processing.
            if len(chain_stack) == 0:
                return
            chain, chain_iter = chain_stack.pop()
            continue
        # Process this link.
        rule = chain.get_rule(link.rule)
        if rule.check(mlist, msg, msgdata):
            if rule.record:
                hits.append(link.rule)
            # The rule matched so run its action.
            if link.action is LinkAction.jump:
                chain = config.chains[link.chain]
                chain_iter = iter(chain)
                continue
            elif link.action is LinkAction.detour:
                # Push the current chain so that we can return to it when
                # the next chain is finished.
                chain_stack.append((chain, chain_iter))
                chain = config.chains[link.chain]
                chain_iter = iter(chain)
                continue
            elif link.action is LinkAction.stop:
                # Stop all processing.
                return
            elif link.action is LinkAction.defer:
                # Just process the next link in the chain.
                pass
            elif link.action is LinkAction.run:
                link.function(mlist, msg, msgdata)
            else:
                raise AssertionError('Bad link action: %s' % link.action)
        else:
            # The rule did not match; keep going.
            if rule.record:
                misses.append(link.rule)



def initialize():
    """Set up chains, both built-in and from the database."""
    for chain_class in (DiscardChain, HoldChain, RejectChain, AcceptChain):
        chain = chain_class()
        assert chain.name not in config.chains, (
            'Duplicate chain name: %s' % chain.name)
        config.chains[chain.name] = chain
    # Set up a couple of other default chains.
    chain = BuiltInChain()
    config.chains[chain.name] = chain
    # Create and initialize the header matching chain.
    chain = HeaderMatchChain()
    config.chains[chain.name] = chain
    # XXX Read chains from the database and initialize them.
    pass
