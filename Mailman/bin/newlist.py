# Copyright (C) 1998-2007 by the Free Software Foundation, Inc.
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

import sha
import sys
import getpass
import optparse

from Mailman import Errors
from Mailman import MailList
from Mailman import Message
from Mailman import Utils
from Mailman import Version
from Mailman import i18n
from Mailman import passwords
from Mailman.bin.mmsitepass import check_password_scheme
from Mailman.configuration import config
from Mailman.initialize import initialize

_ = i18n._

__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] [listname [listadmin-addr [admin-password]]]

Create a new empty mailing list.

You can specify as many of the arguments as you want on the command line:
you will be prompted for the missing ones.

Every Mailman mailing list is situated in a domain, and Mailman supports
multiple virtual domains.  'listname' is required, and if it contains an '@',
it should specify the posting address for your mailing list and the right-hand
side of the email address must be an existing domain.

If 'listname' does not have an '@', the list will be situated in the default
domain, which Mailman created when you configured the system.

Note that listnames are forced to lowercase."""))
    parser.add_option('-l', '--language',
                      type='string', action='store',
                      help=_("""\
Make the list's preferred language LANGUAGE, which must be a two letter
language code."""))
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
non-interactive but still send the notification, assuming listname,
listadmin-addr and admin-password are all specified on the command line."""))
    parser.add_option('-p', '--password-scheme',
                      default='', type='string', help=_("""\
Specify the RFC 2307 style hashing scheme for passwords included in the
output.  Use -P to get a list of supported schemes, which are
case-insensitive."""))
    parser.add_option('-P', '--list-hash-schemes',
                      default=False, action='store_true', help=_("""\
List the supported password hashing schemes and exit.  The scheme labels are
case-insensitive."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if opts.list_hash_schemes:
        for label in passwords.Schemes:
            print str(label).upper()
        sys.exit(0)
    # Can't verify opts.language here because the configuration isn't loaded
    # yet.
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)

    # Set up some defaults we couldn't set up in parseargs()
    if opts.language is None:
        opts.language = config.DEFAULT_SERVER_LANGUAGE
    # Is the language known?
    if opts.language not in config.languages.enabled_codes:
        parser.print_help()
        print >> sys.stderr, _('Unknown language: $opts.language')
        sys.exit(1)

    # Handle variable number of positional arguments
    if args:
        listname = args.pop(0)
    else:
        listname = raw_input(_('Enter the name of the list: '))

    listname = listname.lower()
    if '@' in listname:
        fqdn_listname = listname
        listname, email_host = listname.split('@', 1)
        url_host = config.domains.get(email_host)
        if not url_host:
            print >> sys.stderr, _('Undefined domain: $email_host')
            sys.exit(1)
    else:
        email_host = config.DEFAULT_EMAIL_HOST
        url_host = config.DEFAULT_URL_HOST
        fqdn_listname = '%s@%s' % (listname, email_host)
    web_page_url = config.DEFAULT_URL_PATTERN % url_host
    # Even though MailList.Create() will check to make sure the list doesn't
    # yet exist, do it now for better usability.
    if Utils.list_exists(fqdn_listname):
        parser.print_help()
        print >> sys.stderr, _('List already exists: $listname')

    if args:
        owner_mail = args.pop(0)
    else:
        owner_mail = raw_input(
            _('Enter the email of the person running the list: '))

    if args:
        listpasswd = args.pop(0)
    else:
        while True:
            listpasswd = getpass.getpass(_('Initial $listname password: '))
            confirm = getpass.getpass(_('Confirm $listname password: '))
            if listpasswd == confirm:
                break
            print _('Passwords did not match, try again (Ctrl-C to quit)')

    # List passwords cannot be empty
    listpasswd = listpasswd.strip()
    if not listpasswd:
        parser.print_help()
        print >> sys.stderr, _('The list password cannot be empty')

    mlist = MailList.MailList()
    # Assign the preferred language before Create() since that will use it to
    # set available_languages.
    mlist.preferred_language = opts.language
    try:
        scheme = check_password_scheme(parser, opts.password_scheme)
        pw = passwords.make_secret(listpasswd, scheme)
        try:
            mlist.Create(fqdn_listname, owner_mail, pw)
        except Errors.BadListNameError, s:
            parser.print_help()
            print >> sys.stderr, _('Illegal list name: $s')
            sys.exit(1)
        except Errors.EmailAddressError, s:
            parser.print_help()
            print >> sys.stderr, _('Bad owner email address: $s')
            sys.exit(1)
        except Errors.MMListAlreadyExistsError:
            parser.print_help()
            print >> sys.stderr, _('List already exists: $listname')
            sys.exit(1)
        mlist.Save()
    finally:
        mlist.Unlock()

    # Now do the MTA-specific list creation tasks
    if config.MTA:
        modname = 'Mailman.MTA.' + config.MTA
        __import__(modname)
        sys.modules[modname].create(mlist)

    # And send the notice to the list owner
    if not opts.quiet and not opts.automate:
        print _('Hit enter to notify $listname owner...'),
        sys.stdin.readline()
    if not opts.quiet:
        d = dict(
            listname        = listname,
            password        = listpasswd,
            admin_url       = mlist.GetScriptURL('admin', absolute=True),
            listinfo_url    = mlist.GetScriptURL('listinfo', absolute=True),
            requestaddr     = mlist.GetRequestEmail(),
            siteowner       = mlist.no_reply_address,
            )
        text = Utils.maketext('newlist.txt', d, mlist=mlist)
        # Set the I18N language to the list's preferred language so the header
        # will match the template language.  Stashing and restoring the old
        # translation context is just (healthy? :) paranoia.
        otrans = i18n.get_translation()
        i18n.set_language(mlist.preferred_language)
        try:
            msg = Message.UserNotification(
                owner_mail, mlist.no_reply_address,
                _('Your new mailing list: $listname'),
                text, mlist.preferred_language)
            msg.send(mlist)
        finally:
            i18n.set_translation(otrans)
