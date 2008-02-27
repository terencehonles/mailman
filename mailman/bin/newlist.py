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

import sha
import sys
import getpass
import datetime
import optparse

from mailman import Errors
from mailman import Message
from mailman import Utils
from mailman import Version
from mailman import i18n
from mailman.app.lifecycle import create_list
from mailman.configuration import config
from mailman.initialize import initialize
from mailman.interfaces import ListAlreadyExistsError


_ = i18n._



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] fqdn_listname

Create a new mailing list.

fqdn_listname is the 'fully qualified list name', basically the posting
address of the list.  It must be a valid email address and the domain must be
registered with Mailman.

Note that listnames are forced to lowercase."""))
    parser.add_option('-l', '--language',
                      type='string', action='store',
                      help=_("""\
Make the list's preferred language LANGUAGE, which must be a two letter
language code."""))
    parser.add_option('-o', '--owner',
                      type='string', action='append', default=[],
                      dest='owners', help=_("""\
Specific a listowner email address.  If the address is not currently
registered with Mailman, the address is registered and linked to a user.
Mailman will send a confirmation message to the address, but it will also send
a list creation notice to the address.  More than one owner can be
specified."""))
    parser.add_option('-q', '--quiet',
                      default=False, action='store_true',
                      help=_("""\
Normally the administrator is notified by email (after a prompt) that their
list has been created.  This option suppresses the prompt and
notification."""))
    parser.add_option('-a', '--automate',
                      default=False, action='store_true',
                      help=_("""\
This option suppresses the prompt prior to administrator notification but
still sends the notification.  It can be used to make newlist totally
non-interactive but still send the notification, assuming at least one list
owner is specified with the -o option.."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    # We can't verify opts.language here because the configuration isn't
    # loaded yet.
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)

    # Set up some defaults we couldn't set up in parseargs()
    if opts.language is None:
        opts.language = config.DEFAULT_SERVER_LANGUAGE
    # Is the language known?
    if opts.language not in config.languages.enabled_codes:
        parser.error(_('Unknown language: $opts.language'))
    # Handle variable number of positional arguments
    if len(args) == 0:
        parser.error(_('You must supply a mailing list name'))
    elif len(args) == 1:
        fqdn_listname = args[0].lower()
    elif len(args) > 1:
        parser.error(_('Unexpected arguments'))

    # Create the mailing list, applying styles as appropriate.
    try:
        mlist = create_list(fqdn_listname, opts.owners)
        mlist.preferred_language = opts.language
    except Errors.InvalidEmailAddress:
        parser.error(_('Illegal list name: $fqdn_listname'))
    except ListAlreadyExistsError:
        parser.error(_('List already exists: $fqdn_listname'))
    except Errors.BadDomainSpecificationError, domain:
        parser.error(_('Undefined domain: $domain'))

    config.db.flush()

    # Send notices to the list owners.  XXX This should also be moved to the
    # Mailman.app.create module.
    if not opts.quiet and not opts.automate:
        print _('Hit enter to notify $fqdn_listname owners...'),
        sys.stdin.readline()
    if not opts.quiet:
        d = dict(
            listname        = mlist.fqdn_listname,
            admin_url       = mlist.script_url('admin'),
            listinfo_url    = mlist.script_url('listinfo'),
            requestaddr     = mlist.request_address,
            siteowner       = mlist.no_reply_address,
            )
        text = Utils.maketext('newlist.txt', d, mlist=mlist)
        # Set the I18N language to the list's preferred language so the header
        # will match the template language.  Stashing and restoring the old
        # translation context is just (healthy? :) paranoia.
        with i18n.using_language(mlist.preferred_language):
            msg = Message.UserNotification(
                owner_mail, mlist.no_reply_address,
                _('Your new mailing list: $listname'),
                text, mlist.preferred_language)
            msg.send(mlist)
