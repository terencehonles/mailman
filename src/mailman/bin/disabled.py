# Copyright (C) 2001-2012 by the Free Software Foundation, Inc.
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

import time
import logging
import optparse

from mailman import MailList
from mailman import MemberAdaptor
from mailman import Pending
from mailman import loginit
from mailman.Bouncer import _BounceInfo
from mailman.configuration import config
from mailman.core.i18n import _
from mailman.interfaces.member import NotAMemberError
from mailman.version import MAILMAN_VERSION


# Work around known problems with some RedHat cron daemons
import signal
signal.signal(signal.SIGCHLD, signal.SIG_DFL)

ALL = (MemberAdaptor.BYBOUNCE,
       MemberAdaptor.BYADMIN,
       MemberAdaptor.BYUSER,
       MemberAdaptor.UNKNOWN,
       )



def who_callback(option, opt, value, parser):
    dest = getattr(parser.values, option.dest)
    if opt in ('-o', '--byadmin'):
        dest.add(MemberAdaptor.BYADMIN)
    elif opt in ('-m', '--byuser'):
        dest.add(MemberAdaptor.BYUSER)
    elif opt in ('-u', '--unknown'):
        dest.add(MemberAdaptor.UNKNOWN)
    elif opt in ('-b', '--notbybounce'):
        dest.discard(MemberAdaptor.BYBOUNCE)
    elif opt in ('-a', '--all'):
        dest.update(ALL)


def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options]

Process disabled members, recommended once per day.

This script iterates through every mailing list looking for members whose
delivery is disabled.  If they have been disabled due to bounces, they will
receive another notification, or they may be removed if they've received the
maximum number of notifications.

Use the --byadmin, --byuser, and --unknown flags to also send notifications to
members whose accounts have been disabled for those reasons.  Use --all to
send the notification to all disabled members."""))
    # This is the set of working flags for who to send notifications to.  By
    # default, we notify anybody who has been disable due to bounces.
    parser.set_defaults(who=set([MemberAdaptor.BYBOUNCE]))
    parser.add_option('-o', '--byadmin',
                      callback=who_callback, action='callback', dest='who',
                      help=_("""\
Also send notifications to any member disabled by the list
owner/administrator."""))
    parser.add_option('-m', '--byuser',
                      callback=who_callback, action='callback', dest='who',
                      help=_("""\
Also send notifications to any member who has disabled themself."""))
    parser.add_option('-u', '--unknown',
                      callback=who_callback, action='callback', dest='who',
                      help=_("""\
Also send notifications to any member disabled for unknown reasons
(usually a legacy disabled address)."""))
    parser.add_option('-b', '--notbybounce',
                      callback=who_callback, action='callback', dest='who',
                      help=_("""\
Don't send notifications to members disabled because of bounces (the
default is to notify bounce disabled members)."""))
    parser.add_option('-a', '--all',
                      callback=who_callback, action='callback', dest='who',
                      help=_('Send notifications to all disabled members'))
    parser.add_option('-f', '--force',
                      default=False, action='store_true',
                      help=_("""\
Send notifications to disabled members even if they're not due a new
notification yet."""))
    parser.add_option('-l', '--listname',
                      dest='listnames', action='append', default=[],
                      type='string', help=_("""\
Process only the given list, otherwise do all lists."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    return opts, args, parser



def main():
    opts, args, parser = parseargs()
    config.load(opts.config)

    loginit.initialize(propagate=True)
    elog = logging.getLogger('mailman.error')
    blog = logging.getLogger('mailman.bounce')

    listnames = set(opts.listnames or config.list_manager.names)
    who = tuple(opts.who)

    msg = _('[disabled by periodic sweep and cull, no message available]')
    today = time.mktime(time.localtime()[:3] + (0,) * 6)
    for listname in listnames:
        # List of members to notify
        notify = []
        mlist = MailList.MailList(listname)
        try:
            interval = mlist.bounce_you_are_disabled_warnings_interval
            # Find all the members who are currently bouncing and see if
            # they've reached the disable threshold but haven't yet been
            # disabled.  This is a sweep through the membership catching
            # situations where they've bounced a bunch, then the list admin
            # lowered the threshold, but we haven't (yet) seen more bounces
            # from the member.  Note: we won't worry about stale information
            # or anything else since the normal bounce processing code will
            # handle that.
            disables = []
            for member in mlist.getBouncingMembers():
                if mlist.getDeliveryStatus(member) <> MemberAdaptor.ENABLED:
                    continue
                info = mlist.getBounceInfo(member)
                if info.score >= mlist.bounce_score_threshold:
                    disables.append((member, info))
            if disables:
                for member, info in disables:
                    mlist.disableBouncingMember(member, info, msg)
            # Go through all the members who have delivery disabled, and find
            # those that are due to have another notification.  If they are
            # disabled for another reason than bouncing, and we're processing
            # them (because of the command line switch) then they won't have a
            # bounce info record.  We can piggyback on that for all disable
            # purposes.
            members = mlist.getDeliveryStatusMembers(who)
            for member in members:
                info = mlist.getBounceInfo(member)
                if not info:
                    # See if they are bounce disabled, or disabled for some
                    # other reason.
                    status = mlist.getDeliveryStatus(member)
                    if status == MemberAdaptor.BYBOUNCE:
                        elog.error(
                            '%s disabled BYBOUNCE lacks bounce info, list: %s',
                            member, mlist.internal_name())
                        continue
                    info = _BounceInfo(
                        member, 0, today,
                        mlist.bounce_you_are_disabled_warnings,
                        mlist.pend_new(Pending.RE_ENABLE,
                                       mlist.internal_name(),
                                       member))
                    mlist.setBounceInfo(member, info)
                lastnotice = time.mktime(info.lastnotice + (0,) * 6)
                if opts.force or today >= lastnotice + interval:
                    notify.append(member)
            # Now, send notifications to anyone who is due
            for member in notify:
                blog.info('Notifying disabled member %s for list: %s',
                          member, mlist.internal_name())
                try:
                    mlist.sendNextNotification(member)
                except NotAMemberError:
                    # There must have been some problem with the data we have
                    # on this member.  Most likely it's that they don't have a
                    # password assigned.  Log this and delete the member.
                    blog.info(
                        'Cannot send disable notice to non-member: %s',
                        member)
                    mlist.ApprovedDeleteMember(member, 'cron/disabled')
            mlist.Save()
        finally:
            mlist.Unlock()



if __name__ == '__main__':
    main()
