# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
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

from __future__ import with_statement

import os
import sys
import optparse

from cStringIO import StringIO
from email.utils import parseaddr

from Mailman import Errors
from Mailman import MailList
from Mailman import Message
from Mailman import Utils
from Mailman import Version
from Mailman import i18n
from Mailman.app.membership import add_member
from Mailman.configuration import config
from Mailman.initialize import initialize
from Mailman.interfaces import DeliveryMode

_ = i18n._
__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] listname

Add members to a list.  'listname' is the name of the Mailman list you are
adding members to; the list must already exist.

You must supply at least one of -r and -d options.  At most one of the
files can be '-'.
"""))
    parser.add_option('-r', '--regular-members-file',
                      type='string', dest='regular', help=_("""\
A file containing addresses of the members to be added, one address per line.
This list of people become non-digest members.  If file is '-', read addresses
from stdin."""))
    parser.add_option('-d', '--digest-members-file',
                      type='string', dest='digest', help=_("""\
Similar to -r, but these people become digest members."""))
    parser.add_option('-w', '--welcome-msg',
                      type='string', metavar='<y|n>', help=_("""\
Set whether or not to send the list members a welcome message, overriding
whatever the list's 'send_welcome_msg' setting is."""))
    parser.add_option('-a', '--admin-notify',
                      type='string', metavar='<y|n>', help=_("""\
Set whether or not to send the list administrators a notification on the
success/failure of these subscriptions, overriding whatever the list's
'admin_notify_mchanges' setting is."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if not args:
        parser.error(_('Missing listname'))
    if len(args) > 1:
        parser.error(_('Unexpected arguments'))
    if opts.welcome_msg is not None:
        ch = opts.welcome_msg[0].lower()
        if ch == 'y':
            opts.welcome_msg = True
        elif ch == 'n':
            opts.welcome_msg = False
        else:
            parser.error(_('Illegal value for -w: $opts.welcome_msg'))
    if opts.admin_notify is not None:
        ch = opts.admin_notify[0].lower()
        if ch == 'y':
            opts.admin_notify = True
        elif ch == 'n':
            opts.admin_notify = False
        else:
            parser.error(_('Illegal value for -a: $opts.admin_notify'))
    if opts.regular is None and opts.digest is None:
        parser.error(_('At least one of -r or -d is required'))
    if opts.regular == '-' and opts.digest == '-':
        parser.error(_("-r and -d cannot both be '-'"))
    return parser, opts, args



def readfile(filename):
    if filename == '-':
        fp = sys.stdin
    else:
        fp = open(filename)
    # Strip all the lines of whitespace and discard blank lines
    try:
        return [line.strip() for line in fp if line]
    finally:
        if fp is not sys.stdin:
            fp.close()



class Tee:
    def __init__(self, outfp):
        self._outfp = outfp

    def write(self, msg):
        sys.stdout.write(msg)
        self._outfp.write(msg)



def addall(mlist, subscribers, delivery_mode, ack, admin_notify, outfp):
    tee = Tee(outfp)
    for subscriber in subscribers:
        try:
            fullname, address = parseaddr(subscriber)
            password = Utils.MakeRandomPassword()
            add_member(mlist, address, fullname, password, delivery_mode,
                       config.DEFAULT_SERVER_LANGUAGE, ack, admin_notify)
        except AlreadySubscribedError:
            print >> tee, _('Already a member: $subscriber')
        except Errors.InvalidEmailAddress:
            if userdesc.address == '':
                print >> tee, _('Bad/Invalid email address: blank line')
            else:
                print >> tee, _('Bad/Invalid email address: $member')
        else:
            print >> tee, _('Subscribing: $subscriber')



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)

    listname = args[0].lower().strip()
    mlist = config.db.list_manager.get(listname)
    if mlist is None:
        parser.error(_('No such list: $listname'))

    # Set up defaults.
    if opts.welcome_msg is None:
        send_welcome_msg = mlist.send_welcome_msg
    else:
        send_welcome_msg = opts.welcome_msg
    if opts.admin_notify is None:
        admin_notify = mlist.admin_notify_mchanges
    else:
        admin_notify = opts.admin_notify

    with i18n.using_language(mlist.preferred_language):
        if opts.digest:
            dmembers = readfile(opts.digest)
        else:
            dmembers = []
        if opts.regular:
            nmembers = readfile(opts.regular)
        else:
            nmembers = []

        if not dmembers and not nmembers:
            print _('Nothing to do.')
            sys.exit(0)

        s = StringIO()
        if nmembers:
            addall(mlist, nmembers, DeliveryMode.regular,
                   send_welcome_msg, admin_notify, s)

        if dmembers:
            addall(mlist, dmembers, DeliveryMode.mime_digests,
                   send_welcome_msg, admin_notify, s)

        config.db.flush()

        if admin_notify:
            subject = _('$mlist.real_name subscription notification')
            msg = Message.UserNotification(
                mlist.owner, mlist.no_reply_address, subject, s.getvalue(),
                mlist.preferred_language)
            msg.send(mlist)



if __name__ == '__main__':
    main()
