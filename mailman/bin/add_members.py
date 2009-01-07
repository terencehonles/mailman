# Copyright (C) 1998-2009 by the Free Software Foundation, Inc.
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

import os
import sys
import codecs

from cStringIO import StringIO
from email.utils import parseaddr

from mailman import Message
from mailman import Utils
from mailman import i18n
from mailman.app.membership import add_member
from mailman.config import config
from mailman.core import errors
from mailman.interfaces.member import AlreadySubscribedError, DeliveryMode
from mailman.options import SingleMailingListOptions

_ = i18n._



class ScriptOptions(SingleMailingListOptions):
    usage=_("""\
%prog [options]

Add members to a list.  'listname' is the name of the Mailman list you are
adding members to; the list must already exist.

You must supply at least one of -r and -d options.  At most one of the
files can be '-'.
""")

    def add_options(self):
        super(ScriptOptions, self).add_options()
        self.parser.add_option(
            '-r', '--regular-members-file',
            type='string', dest='regular', help=_("""\
A file containing addresses of the members to be added, one address per line.
This list of people become non-digest members.  If file is '-', read addresses
from stdin."""))
        self.parser.add_option(
            '-d', '--digest-members-file',
            type='string', dest='digest', help=_("""\
Similar to -r, but these people become digest members."""))
        self.parser.add_option(
            '-w', '--welcome-msg',
            type='yesno', metavar='<y|n>', help=_("""\
Set whether or not to send the list members a welcome message, overriding
whatever the list's 'send_welcome_msg' setting is."""))
        self.parser.add_option(
            '-a', '--admin-notify',
            type='yesno', metavar='<y|n>', help=_("""\
Set whether or not to send the list administrators a notification on the
success/failure of these subscriptions, overriding whatever the list's
'admin_notify_mchanges' setting is."""))

    def sanity_check(self):
        if not self.options.listname:
            self.parser.error(_('Missing listname'))
        if len(self.arguments) > 0:
            self.parser.print_error(_('Unexpected arguments'))
        if self.options.regular is None and self.options.digest is None:
            parser.error(_('At least one of -r or -d is required'))
        if self.options.regular == '-' and self.options.digest == '-':
            parser.error(_("-r and -d cannot both be '-'"))



def readfile(filename):
    if filename == '-':
        fp = sys.stdin
    else:
        # XXX Need to specify other encodings.
        fp = codecs.open(filename, encoding='utf-8')
    # Strip all the lines of whitespace and discard blank lines
    try:
        return set(line.strip() for line in fp if line)
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
            # Watch out for the empty 8-bit string.
            if not fullname:
                fullname = u''
            password = Utils.MakeRandomPassword()
            add_member(mlist, address, fullname, password, delivery_mode,
                       unicode(config.mailman.default_language))
            # XXX Support ack and admin_notify
        except AlreadySubscribedError:
            print >> tee, _('Already a member: $subscriber')
        except errors.InvalidEmailAddress:
            if not address:
                print >> tee, _('Bad/Invalid email address: blank line')
            else:
                print >> tee, _('Bad/Invalid email address: $subscriber')
        else:
            print >> tee, _('Subscribing: $subscriber')



def main():
    options = ScriptOptions()
    options.initialize()

    fqdn_listname = options.options.listname
    mlist = config.db.list_manager.get(fqdn_listname)
    if mlist is None:
        parser.error(_('No such list: $fqdn_listname'))

    # Set up defaults.
    send_welcome_msg = (options.options.welcome_msg
                        if options.options.welcome_msg is not None
                        else mlist.send_welcome_msg)
    admin_notify = (options.options.admin_notify
                    if options.options.admin_notify is not None
                    else mlist.admin_notify)

    with i18n.using_language(mlist.preferred_language):
        if options.options.digest:
            dmembers = readfile(options.options.digest)
        else:
            dmembers = set()
        if options.options.regular:
            nmembers = readfile(options.options.regular)
        else:
            nmembers = set()

        if not dmembers and not nmembers:
            print _('Nothing to do.')
            sys.exit(0)

        outfp = StringIO()
        if nmembers:
            addall(mlist, nmembers, DeliveryMode.regular,
                   send_welcome_msg, admin_notify, outfp)

        if dmembers:
            addall(mlist, dmembers, DeliveryMode.mime_digests,
                   send_welcome_msg, admin_notify, outfp)

        config.db.commit()

        if admin_notify:
            subject = _('$mlist.real_name subscription notification')
            msg = Message.UserNotification(
                mlist.owner, mlist.no_reply_address, subject,
                outfp.getvalue(), mlist.preferred_language)
            msg.send(mlist)



if __name__ == '__main__':
    main()
