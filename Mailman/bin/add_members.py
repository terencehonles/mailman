# Copyright (C) 1998-2006 by the Free Software Foundation, Inc.
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

import os
import sys
import optparse

from cStringIO import StringIO
from email.Utils import parseaddr

from Mailman import Errors
from Mailman import MailList
from Mailman import Message
from Mailman import Utils
from Mailman import i18n
from Mailman import mm_cfg

_ = i18n._
__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=mm_cfg.MAILMAN_VERSION,
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
    opts, args = parser.parse_args()
    if not args:
        parser.print_help()
        print >> sys.stderr, _('Missing listname')
        sys.exit(1)
    if len(args) > 1:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    if opts.welcome_msg is not None:
        ch = opts.welcome_msg[0].lower()
        if ch == 'y':
            opts.welcome_msg = True
        elif ch == 'n':
            opts.welcome_msg = False
        else:
            parser.print_help()
            print >> sys.stderr, _('Illegal value for -w: $opts.welcome_msg')
            sys.exit(1)
    if opts.admin_notify is not None:
        ch = opts.admin_notify[0].lower()
        if ch == 'y':
            opts.admin_notify = True
        elif ch == 'n':
            opts.admin_notify = False
        else:
            parser.print_help()
            print >> sys.stderr, _('Illegal value for -a: $opts.admin_notify')
            sys.exit(1)
    if opts.regular is None and opts.digest is None:
        parser.print_help()
        print >> sys.stderr, _('At least one of -r or -d is required')
        sys.exit(1)
    if opts.regular == '-' and opts.digest == '-':
        parser.print_help()
        print >> sys.stderr, _("-r and -d cannot both be '-'")
        sys.exit(1)
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


class UserDesc:
    pass



def addall(mlist, members, digest, ack, outfp):
    tee = Tee(outfp)
    for member in members:
        userdesc = UserDesc()
        userdesc.fullname, userdesc.address = parseaddr(member)
        userdesc.digest = digest

        try:
            mlist.ApprovedAddMember(userdesc, ack, 0)
        except Errors.MMAlreadyAMember:
            print >> tee, _('Already a member: $member')
        except Errors.MMBadEmailError:
            if userdesc.address == '':
                print >> tee, _('Bad/Invalid email address: blank line')
            else:
                print >> tee, _('Bad/Invalid email address: $member')
        except Errors.MMHostileAddress:
            print >> tee, _('Hostile address (illegal characters): $member')
        else:
            print >> tee, _('Subscribed: $member')



def main():
    parser, opts, args = parseargs()

    listname = args[0].lower().strip()
    try:
        mlist = MailList.MailList(listname)
    except Errors.MMUnknownListError:
        parser.print_help()
        print >> sys.stderr, _('No such list: $listname')
        sys.exit(1)

    # Set up defaults
    if opts.welcome_msg is None:
        send_welcome_msg = mlist.send_welcome_msg
    else:
        send_welcome_msg = opts.welcome_msg
    if opts.admin_notify is None:
        admin_notify = mlist.admin_notify_mchanges
    else:
        admin_notify = opts.admin_notify

    otrans = i18n.get_translation()
    # Read the regular and digest member files
    try:
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
        i18n.set_language(mlist.preferred_language)
        if nmembers:
            addall(mlist, nmembers, False, send_welcome_msg, s)

        if dmembers:
            addall(mlist, dmembers, True, send_welcome_msg, s)

        if admin_notify:
            subject = _('$mlist.real_name subscription notification')
            msg = Message.UserNotification(
                mlist.owner, mlist.GetNoReplyEmail(), subject, s.getvalue(),
                mlist.preferred_language)
            msg.send(mlist)

        mlist.Save()
    finally:
        mlist.Unlock()
        i18n.set_translation(otrans)


if __name__ == '__main__':
    main()
