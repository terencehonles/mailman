# Copyright (C) 2001,2002 by the Free Software Foundation, Inc.
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

"""Bounce queue runner."""

import re
from email.Utils import parseaddr

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import LockFile
from Mailman.Bouncers import BouncerAPI
from Mailman.Queue.Runner import Runner
from Mailman.Queue.sbcache import get_switchboard
from Mailman.Logging.Syslog import syslog



class BounceRunner(Runner):
    def __init__(self, slice=None, numslices=1, cachelists=1):
        Runner.__init__(self, mm_cfg.BOUNCEQUEUE_DIR,
                        slice, numslices, cachelists)

    def _dispose(self, mlist, msg, msgdata):
        outq = get_switchboard(mm_cfg.OUTQUEUE_DIR)
        # BAW: Not all the functions of this qrunner require the list to be
        # locked.  Still, it's more convenient to lock it here and now and
        # deal with lock failures in one place.
        try:
            mlist.Lock(timeout=mm_cfg.LIST_LOCK_TIMEOUT)
        except LockFile.TimeOutError:
            # Oh well, try again later
            return 1
        try:
            # There are a few possibilities here:
            #
            # - the message could have been VERP'd in which case, we know
            #   exactly who the message was destined for.  That make our job
            #   easy.
            # - the message could have been originally destined for a list
            #   owner, but a list owner address itself bounced.  That's bad,
            #   and for now we'll simply log the problem and attempt to
            #   deliver the message to the site owner.
            #
            # All messages to list-owner@vdom.ain have their envelope sender
            # set to site-owner@dom.ain (no virtual domain).  Is this a bounce
            # for a message to a list owner, coming to the site owner?
            if msg.get('to', '') == Utils.get_site_email(extra='-owner'):
                # Send it on to the site owners, but craft the envelope sender
                # to be the -loop detection address, so if /they/ bounce, we
                # won't get stuck in a bounce loop.
                outq.enqueue(msg, msgdata,
                             recips=[Utils.get_site_email()],
                             envsender=Utils.get_site_email(extra='loop'),
                             )
            # List isn't doing bounce processing?
            if not mlist.bounce_processing:
                return
            # If VERPing, the method will take care of things.
            elif self.__verpbounce(mlist, msg):
                mlist.Save()
                return
            # Otherwise do bounce detection of the original message
            elif self.__scanbounce(mlist, msg):
                mlist.Save()
                return
            # Otherwise, we should just forward this message to the list
            # owner, because there's nothing we can do with it.  Be sure to
            # point the envelope sender at the site owner for any bounces to
            # list owners.
            recips = mlist.owner[:]
            recips.extend(mlist.moderator)
            outq.enqueue(msg, msgdata,
                         recips=recips,
                         envsender=Utils.get_site_email(extra='admin'),
                         )
        finally:
            mlist.Unlock()

    def __verpbounce(self, mlist, msg):
        bmailbox, bdomain = Utils.ParseEmail(mlist.getListAddress('bounces'))
        # Sadly not every MTA bounces VERP messages correctly.  Fall back to
        # Delivered-to: and Apparently-To:, and then short-circuit if we still
        # don't have anything to work with.  Note that there can be multiple
        # Delivered-To: headers so we need to search them all (and we don't
        # worry about false positives for forwarded email, because only one
        # should match VERP_REGEXP).
        vals = []
        for header in ('to', 'delivered-to', 'apparently-to'):
            vals.extend(msg.get_all(header, []))
        for field in vals:
            to = parseaddr(field)[1]
            if not to:
                continue                          # empty header
            mo = re.search(mm_cfg.VERP_REGEXP, to)
            if not mo:
                continue                          # no match of regexp
            if bmailbox <> mo.group('bounces'):
                continue                          # not a bounce to our list
            # All is good
            addr = '%s@%s' % mo.group('mailbox', 'host')
            # Now, if this message has come to the site list, then search not
            # only it, but all the mailing lists on the system, registering a
            # bounce with each for this address.
            if mlist.internal_name() == mm_cfg.MAILMAN_SITE_LIST:
                found = 0
                for listname in Utils.list_names():
                    xlist = MailList.MailList(listname, lock=0)
                    if xlist.isMember(addr):
                        xlist.Lock()
                        try:
                            xlist.registerBounce(addr, msg)
                            found = 1
                            xlist.Save()
                        finally:
                            xlist.Unlock()
                return found
            elif mlist.isMember(addr):
                mlist.registerBounce(addr, msg)
                return 1
        return 0

    def __scanbounce(self, mlist, msg):
        if mlist.internal_name() == mm_cfg.MAILMAN_SITE_LIST:
            found = 0
            for listname in Utils.list_names():
                xlist = MailList.MailList(listname, lock=0)
                xlist.Lock()
                try:
                    status = BouncerAPI.ScanMessages(xlist, msg)
                    if status:
                        found = 1
                    xlist.Save()
                finally:
                    xlist.Unlock()
            return found
        else:
            return BouncerAPI.ScanMessages(mlist, msg)
