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
from Mailman.configuration import config

_ = i18n._

__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%%prog [options] [listname [listadmin-addr [admin-password]]]

Create a new, unpopulated mailing list.

You can specify as many of the arguments as you want on the command line:
you will be prompted for the missing ones.

Every Mailman list has two parameters which define the default host name for
outgoing email, and the default URL for all web interfaces.  When you
configured Mailman, certain defaults were calculated, but if you are running
multiple virtual Mailman sites, then the defaults may not be appropriate for
the list you are creating.

You also specify the domain to create your new list in by typing the command
like so:

    newlist --urlhost=www.mydom.ain mylist

where `www.mydom.ain' should be the base hostname for the URL to this virtual
hosts's lists.  E.g. with this setting people will view the general list
overviews at http://www.mydom.ain/mailman/listinfo.  Also, www.mydom.ain
should be a key in the VIRTUAL_HOSTS mapping in mm_cfg.py/Defaults.py if
the email hostname to be automatically determined.

If you want the email hostname to be different from the one looked up by the
VIRTUAL_HOSTS or if urlhost is not registered in VIRTUAL_HOSTS, you can specify
`emailhost' like so:

    newlist --urlhost=www.mydom.ain --emailhost=mydom.ain mylist

where `mydom.ain' is the mail domain name. If you don't specify emailhost but
urlhost is not in the virtual host list, then mm_cfg.DEFAULT_EMAIL_HOST will
be used for the email interface.

For backward compatibility, you can also specify the domain to create your
new list in by spelling the listname like so:

    mylist@www.mydom.ain

where www.mydom.ain is used for `urlhost' but it will also be used for
`emailhost' if it is not found in the virtual host table. Note that
'--urlhost' and '--emailhost' have precedence to this notation.

If you spell the list name as just `mylist', then the email hostname will be
taken from DEFAULT_EMAIL_HOST and the url will be taken from DEFAULT_URL (as
defined in your Defaults.py file or overridden by settings in mm_cfg.py).

Note that listnames are forced to lowercase."""))
    parser.add_option('-l', '--language',
                      type='string', action='store',
                      help=_("""\
Make the list's preferred language LANGUAGE, which must be a two letter
language code."""))
    parser.add_option('-u', '--urlhost',
                      type='string', action='store',
                      help=_('The hostname for the web interface'))
    parser.add_option('-e', '--emailhost',
                      type='string', action='store',
                      help=_('The hostname for the email server'))
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
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    # Can't verify opts.language here because the configuration isn't loaded
    # yet.
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    config.load(opts.config)

    # Set up some defaults we couldn't set up in parseargs()
    if opts.language is None:
        opts.language = config.DEFAULT_SERVER_LANGUAGE
    # Is the language known?
    if opts.language not in config.LC_DESCRIPTIONS:
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
        # Note that --urlhost and --emailhost have precedence
        listname, domain = listname.split('@', 1)
        urlhost = opts.urlhost or domain
        emailhost = opts.emailhost or config.VIRTUAL_HOSTS.get(domain, domain)

    urlhost = opts.urlhost or config.DEFAULT_URL_HOST
    host_name = (opts.emailhost or
                 config.VIRTUAL_HOSTS.get(urlhost, config.DEFAULT_EMAIL_HOST))
    web_page_url = config.DEFAULT_URL_PATTERN % urlhost

    if Utils.list_exists(listname):
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
    try:
        pw = sha.new(listpasswd).hexdigest()
        # Guarantee that all newly created files have the proper permission.
        # proper group ownership should be assured by the autoconf script
        # enforcing that all directories have the group sticky bit set.
        oldmask = os.umask(002)
        try:
            try:
                mlist.Create(listname, owner_mail, pw)
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
        finally:
            os.umask(oldmask)

        # Assign domain-specific attributes
        mlist.host_name = host_name
        mlist.web_page_url = web_page_url

        # And assign the preferred language
        mlist.preferred_language = opts.language
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
        siteowner = Utils.get_site_email(mlist.host_name, 'owner')
        d = dict(
            listname        = listname,
            password        = listpasswd,
            admin_url       = mlist.GetScriptURL('admin', absolute=True),
            listinfo_url    = mlist.GetScriptURL('listinfo', absolute=True),
            requestaddr     = mlist.GetRequestEmail(),
            siteowner       = siteowner,
            )
        text = Utils.maketext('newlist.txt', d, mlist=mlist)
        # Set the I18N language to the list's preferred language so the header
        # will match the template language.  Stashing and restoring the old
        # translation context is just (healthy? :) paranoia.
        otrans = i18n.get_translation()
        i18n.set_language(mlist.preferred_language)
        try:
            msg = Message.UserNotification(
                owner_mail, siteowner,
                _('Your new mailing list: $listname'),
                text, mlist.preferred_language)
            msg.send(mlist)
        finally:
            i18n.set_translation(otrans)



if __name__ == '__main__':
    main()
