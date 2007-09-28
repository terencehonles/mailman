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

from __future__ import with_statement

import csv
import optparse

from Mailman import Message
from Mailman import Utils
from Mailman import Version
from Mailman import i18n
from Mailman import passwords
from Mailman.app.membership import add_member
from Mailman.configuration import config
from Mailman.constants import DeliveryMode
from Mailman.initialize import initialize


_ = i18n._
__i18n_templates__ = True

DELIVERY_MODES = {
    'regular':  DeliveryMode.regular,
    'plain':    DeliveryMode.plaintext_digests,
    'mime':     DeliveryMode.mime_digests,
    }



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] csv-file

Set the membership of a mailing list to that described in a CSV file.  Each
row of the CSV file has the following format.  Only the address column is
required.

    - email address
    - full name (default: the empty string)
    - delivery mode (default: regular delivery) [1]

[1] The delivery mode is a case insensitive string of the following values:

    regular     - regular, i.e. immediate delivery
    mime        - MIME digest delivery
    plain       - plain text (RFC 1153) digest delivery

Any address not included in the CSV file is removed from the list membership.
"""))
    parser.add_option('-l', '--listname',
                      type='string', help=_("""\
Mailng list to set the membership for."""))
    parser.add_option('-w', '--welcome-msg',
                      type='string', metavar='<y|n>', help=_("""\
Set whether or not to send the list members a welcome message, overriding
whatever the list's 'send_welcome_msg' setting is."""))
    parser.add_option('-a', '--admin-notify',
                      type='string', metavar='<y|n>', help=_("""\
Set whether or not to send the list administrators a notification on the
success/failure of these subscriptions, overriding whatever the list's
'admin_notify_mchanges' setting is."""))
    parser.add_option('-v', '--verbose', action='store_true',
                      help=_('Increase verbosity'))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
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
    return parser, opts, args



def parse_file(filename):
    members = {}
    with open(filename) as fp:
        for row in csv.reader(fp):
            if len(row) == 0:
                continue
            elif len(row) == 1:
                address = row[0]
                real_name = None
                delivery_mode = DeliveryMode.regular
            elif len(row) == 2:
                address, real_name = row
                delivery_mode = DeliveryMode.regular
            else:
                # Ignore extra columns
                address, real_name = row[0:2]
                delivery_mode = DELIVERY_MODES.get(row[2].lower())
                if delivery_mode is None:
                    delivery_mode = DeliveryMode.regular
            members[address] = real_name, delivery_mode
    return members



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)

    mlist = config.db.list_manager.get(opts.listname)
    if mlist is None:
        parser.error(_('No such list: $opts.listname'))

    # Set up defaults.
    if opts.welcome_msg is None:
        send_welcome_msg = mlist.send_welcome_msg
    else:
        send_welcome_msg = opts.welcome_msg
    if opts.admin_notify is None:
        admin_notify = mlist.admin_notify_mchanges
    else:
        admin_notify = opts.admin_notify

    # Parse the csv files.
    member_data = {}
    for filename in args:
        member_data.update(parse_file(filename))

    future_members = set(member_data)
    current_members = set(obj.address for obj in mlist.members.addresses)
    add_members = future_members - current_members
    delete_members = current_members - future_members
    change_members = current_members & future_members
    
    with i18n.using_language(mlist.preferred_language):
        # Start by removing all the delete members.
        for address in delete_members:
            print _('deleting address: $address')
            member = mlist.members.get_member(address)
            member.unsubscribe()
        # For all members that are in both lists, update their full name and
        # delivery mode.
        for address in change_members:
            print _('updating address: $address')
            real_name, delivery_mode = member_data[address]
            member = mlist.members.get_member(address)
            member.preferences.delivery_mode = delivery_mode
            user = config.db.user_manager.get_user(address)
            user.real_name = real_name
        for address in add_members:
            print _('adding address: $address')
            real_name, delivery_mode = member_data[address]
            password = passwords.make_secret(
                Utils.MakeRandomPassword(),
                passwords.lookup_scheme(config.PASSWORD_SCHEME))
            add_member(mlist, address, real_name, password, delivery_mode,
                       mlist.preferred_language, send_welcome_msg,
                       admin_notify)

    config.db.flush()



if __name__ == '__main__':
    main()
