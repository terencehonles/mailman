# Copyright (C) 2001-2009 by the Free Software Foundation, Inc.
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

"""Bounce queue runner."""

import os
import re
import cPickle
import logging
import datetime

from email.Utils import parseaddr
from lazr.config import as_timedelta

from mailman.Bouncers import BouncerAPI
from mailman.config import config
from mailman.core.i18n import _
from mailman.email.utils import split_email
from mailman.queue import Runner


COMMASPACE = ', '

log = logging.getLogger('mailman.bounce')
elog = logging.getLogger('mailman.error')



class BounceMixin:
    def __init__(self):
        # Registering a bounce means acquiring the list lock, and it would be
        # too expensive to do this for each message.  Instead, each bounce
        # runner maintains an event log which is essentially a file with
        # multiple pickles.  Each bounce we receive gets appended to this file
        # as a 4-tuple record: (listname, addr, today, msg)
        #
        # today is itself a 3-tuple of (year, month, day)
        #
        # Every once in a while (see _do_periodic()), the bounce runner cracks
        # open the file, reads all the records and registers all the bounces.
        # Then it truncates the file and continues on.  We don't need to lock
        # the bounce event file because bounce qrunners are single threaded
        # and each creates a uniquely named file to contain the events.
        #
        # XXX When Python 2.3 is minimal require, we can use the new
        # tempfile.TemporaryFile() function.
        #
        # XXX We used to classify bounces to the site list as bounce events
        # for every list, but this caused severe problems.  Here's the
        # scenario: aperson@example.com is a member of 4 lists, and a list
        # owner of the foo list.  example.com has an aggressive spam filter
        # which rejects any message that is spam or contains spam as an
        # attachment.  Now, a spambot sends a piece of spam to the foo list,
        # but since that spambot is not a member, the list holds the message
        # for approval, and sends a notification to aperson@example.com as
        # list owner.  That notification contains a copy of the spam.  Now
        # example.com rejects the message, causing a bounce to be sent to the
        # site list's bounce address.  The bounce runner would then dutifully
        # register a bounce for all 4 lists that aperson@example.com was a
        # member of, and eventually that person would get disabled on all
        # their lists.  So now we ignore site list bounces.  Ce La Vie for
        # password reminder bounces.
        self._bounce_events_file = os.path.join(
            config.DATA_DIR, 'bounce-events-%05d.pck' % os.getpid())
        self._bounce_events_fp = None
        self._bouncecnt = 0
        self._nextaction = (
            datetime.datetime.now() +
            as_timedelta(config.bounces.register_bounces_every))

    def _queue_bounces(self, listname, addrs, msg):
        today = datetime.date.today()
        if self._bounce_events_fp is None:
            self._bounce_events_fp = open(self._bounce_events_file, 'a+b')
        for addr in addrs:
            cPickle.dump((listname, addr, today, msg),
                         self._bounce_events_fp, 1)
        self._bounce_events_fp.flush()
        os.fsync(self._bounce_events_fp.fileno())
        self._bouncecnt += len(addrs)

    def _register_bounces(self):
        log.info('%s processing %s queued bounces', self, self._bouncecnt)
        # Read all the records from the bounce file, then unlink it.  Sort the
        # records by listname for more efficient processing.
        events = {}
        self._bounce_events_fp.seek(0)
        while True:
            try:
                listname, addr, day, msg = cPickle.load(self._bounce_events_fp)
            except ValueError, e:
                log.error('Error reading bounce events: %s', e)
            except EOFError:
                break
            events.setdefault(listname, []).append((addr, day, msg))
        # Now register all events sorted by list
        for listname in events.keys():
            mlist = self._open_list(listname)
            mlist.Lock()
            try:
                for addr, day, msg in events[listname]:
                    mlist.registerBounce(addr, msg, day=day)
                mlist.Save()
            finally:
                mlist.Unlock()
        # Reset and free all the cached memory
        self._bounce_events_fp.close()
        self._bounce_events_fp = None
        os.unlink(self._bounce_events_file)
        self._bouncecnt = 0

    def _clean_up(self):
        if self._bouncecnt > 0:
            self._register_bounces()

    def _do_periodic(self):
        now = datetime.datetime.now()
        if self._nextaction > now or self._bouncecnt == 0:
            return
        # Let's go ahead and register the bounces we've got stored up
        self._nextaction = now + as_timedelta(
            config.bounces.register_bounces_every)
        self._register_bounces()

    def _probe_bounce(self, mlist, token):
        locked = mlist.Locked()
        if not locked:
            mlist.Lock()
        try:
            op, addr, bmsg = mlist.pend_confirm(token)
            info = mlist.getBounceInfo(addr)
            mlist.disableBouncingMember(addr, info, bmsg)
            # Only save the list if we're unlocking it
            if not locked:
                mlist.Save()
        finally:
            if not locked:
                mlist.Unlock()



class BounceRunner(Runner, BounceMixin):
    """The bounce runner."""

    def __init__(self, slice=None, numslices=1):
        Runner.__init__(self, slice, numslices)
        BounceMixin.__init__(self)

    def _dispose(self, mlist, msg, msgdata):
        # Make sure we have the most up-to-date state
        mlist.Load()
        # There are a few possibilities here:
        #
        # - the message could have been VERP'd in which case, we know exactly
        #   who the message was destined for.  That make our job easy.
        # - the message could have been originally destined for a list owner,
        #   but a list owner address itself bounced.  That's bad, and for now
        #   we'll simply log the problem and attempt to deliver the message to
        #   the site owner.
        #
        # All messages sent to list owners have their sender set to the site
        # owner address.  That way, if a list owner address bounces, at least
        # some human has a chance to deal with it.  Is this a bounce for a
        # message to a list owner, coming to the site owner?
        if msg.get('to', '') == config.mailman.site_owner:
            # Send it on to the site owners, but craft the envelope sender to
            # be the noreply address, so if the site owner bounce, we won't
            # get stuck in a bounce loop.
            config.switchboards['out'].enqueue(
                msg, msgdata,
                recipients=[config.mailman.site_owner],
                envsender=config.mailman.noreply_address,
                )
        # List isn't doing bounce processing?
        if not mlist.bounce_processing:
            return
        # Try VERP detection first, since it's quick and easy
        addrs = verp_bounce(mlist, msg)
        if addrs:
            # We have an address, but check if the message is non-fatal.
            if BouncerAPI.ScanMessages(mlist, msg) is BouncerAPI.Stop:
                return
        else:
            # See if this was a probe message.
            token = verp_probe(mlist, msg)
            if token:
                self._probe_bounce(mlist, token)
                return
            # That didn't give us anything useful, so try the old fashion
            # bounce matching modules.
            addrs = BouncerAPI.ScanMessages(mlist, msg)
            if addrs is BouncerAPI.Stop:
                # This is a recognized, non-fatal notice. Ignore it.
                return
        # If that still didn't return us any useful addresses, then send it on
        # or discard it.
        if not addrs:
            log.info('bounce message w/no discernable addresses: %s',
                     msg.get('message-id'))
            maybe_forward(mlist, msg)
            return
        # BAW: It's possible that there are None's in the list of addresses,
        # although I'm unsure how that could happen.  Possibly ScanMessages()
        # can let None's sneak through.  In any event, this will kill them.
        addrs = filter(None, addrs)
        self._queue_bounces(mlist.fqdn_listname, addrs, msg)

    _do_periodic = BounceMixin._do_periodic

    def _clean_up(self):
        BounceMixin._clean_up(self)
        Runner._clean_up(self)



def verp_bounce(mlist, msg):
    bmailbox, bdomain = split_email(mlist.GetBouncesEmail())
    # Sadly not every MTA bounces VERP messages correctly, or consistently.
    # Fall back to Delivered-To: (Postfix), Envelope-To: (Exim) and
    # Apparently-To:, and then short-circuit if we still don't have anything
    # to work with.  Note that there can be multiple Delivered-To: headers so
    # we need to search them all (and we don't worry about false positives for
    # forwarded email, because only one should match VERP_REGEXP).
    vals = []
    for header in ('to', 'delivered-to', 'envelope-to', 'apparently-to'):
        vals.extend(msg.get_all(header, []))
    for field in vals:
        to = parseaddr(field)[1]
        if not to:
            continue                          # empty header
        mo = re.search(config.mta.verp_regexp, to)
        if not mo:
            continue                          # no match of regexp
        try:
            if bmailbox <> mo.group('bounces'):
                continue                      # not a bounce to our list
            # All is good
            addr = '%s@%s' % mo.group('mailbox', 'host')
        except IndexError:
            elog.error("verp_regexp doesn't yield the right match groups: %s",
                       config.mta.verp_regexp)
            return []
        return [addr]



def verp_probe(mlist, msg):
    bmailbox, bdomain = split_email(mlist.GetBouncesEmail())
    # Sadly not every MTA bounces VERP messages correctly, or consistently.
    # Fall back to Delivered-To: (Postfix), Envelope-To: (Exim) and
    # Apparently-To:, and then short-circuit if we still don't have anything
    # to work with.  Note that there can be multiple Delivered-To: headers so
    # we need to search them all (and we don't worry about false positives for
    # forwarded email, because only one should match VERP_REGEXP).
    vals = []
    for header in ('to', 'delivered-to', 'envelope-to', 'apparently-to'):
        vals.extend(msg.get_all(header, []))
    for field in vals:
        to = parseaddr(field)[1]
        if not to:
            continue                          # empty header
        mo = re.search(config.mta.verp_probe_regexp, to)
        if not mo:
            continue                          # no match of regexp
        try:
            if bmailbox <> mo.group('bounces'):
                continue                      # not a bounce to our list
            # Extract the token and see if there's an entry
            token = mo.group('token')
            data = mlist.pend_confirm(token, expunge=False)
            if data is not None:
                return token
        except IndexError:
            elog.error(
                "verp_probe_regexp doesn't yield the right match groups: %s",
                config.mta.verp_probe_regexp)
    return None



def maybe_forward(mlist, msg):
    # Does the list owner want to get non-matching bounce messages?
    # If not, simply discard it.
    if mlist.bounce_unrecognized_goes_to_list_owner:
        adminurl = mlist.GetScriptURL('admin', absolute=1) + '/bounce'
        mlist.ForwardMessage(msg,
                             text=_("""\
The attached message was received as a bounce, but either the bounce format
was not recognized, or no member addresses could be extracted from it.  This
mailing list has been configured to send all unrecognized bounce messages to
the list administrator(s).

For more information see:
%(adminurl)s

"""),
                             subject=_('Uncaught bounce notification'),
                             tomoderators=0)
        log.error('forwarding unrecognized, message-id: %s',
                  msg.get('message-id', 'n/a'))
    else:
        log.error('discarding unrecognized, message-id: %s',
                  msg.get('message-id', 'n/a'))
