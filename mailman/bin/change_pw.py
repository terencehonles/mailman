# Copyright (C) 2001-2008 by the Free Software Foundation, Inc.
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

from __future__ import with_statement

import sha
import sys
import optparse

from mailman import Errors
from mailman import MailList
from mailman import Message
from mailman import Utils
from mailman import i18n
from mailman.configuration import config
from mailman.version import MAILMAN_VERSION

_ = i18n._
SPACE = ' '



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%%prog [options]

Change a list's password.

Prior to Mailman 2.1, list passwords were kept in crypt'd format -- usually.
Some Python installations didn't have the crypt module available, so they'd
fall back to md5.  Then suddenly the Python installation might grow a crypt
module and all list passwords would be broken.

In Mailman 2.1, all list and site passwords are stored in SHA1 hexdigest
form.  This breaks list passwords for all existing pre-Mailman 2.1 lists, and
since those passwords aren't stored anywhere in plain text, they cannot be
retrieved and updated.

Thus, this script generates new passwords for a list, and optionally sends it
to all the owners of the list."""))
    parser.add_option('-a', '--all',
                      default=False, action='store_true',
                      help=_('Change the password for all lists'))
    parser.add_option('-d', '--domain',
                      default=[], type='string', action='append',
                      dest='domains', help=_("""\
Change the password for all lists in the virtual domain DOMAIN.  It is okay
to give multiple -d options."""))
    parser.add_option('-l', '--listname',
                      default=[], type='string', action='append',
                      dest='listnames', help=_("""\
Change the password only for the named list.  It is okay to give multiple -l
options."""))
    parser.add_option('-p', '--password',
                      type='string', metavar='NEWPASSWORD', help=_("""\
Use the supplied plain text password NEWPASSWORD as the new password for any
lists that are being changed (as specified by the -a, -d, and -l options).  If
not given, lists will be assigned a randomly generated new password."""))
    parser.add_option('-q', '--quiet',
                      default=False, action='store_true', help=_("""\
Don't notify list owners of the new password.  You'll have to have some other
way of letting the list owners know the new password (presumably
out-of-band)."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    if opts.password == '':
        parser.print_help()
        print >> sys.stderr, _('Empty list passwords are not allowed')
        sys.exit(1)
    return parser, opts, args



_listcache = {}
_missing = object()

def openlist(listname):
    missing = []
    mlist = _listcache.get(listname, _missing)
    if mlist is _missing:
        try:
            mlist = MailList.MailList(listname, lock=False)
        except Errors.MMListError:
            print >> sys.stderr, _('No such list: $listname')
            return None
        _listcache[listname] = mlist
    return mlist



def main():
    parser, opts, args = parseargs()
    config.load(opts.config)

    # Cull duplicates
    domains = set(opts.domains)
    listnames = set(config.list_manager.names if opts.all else opts.listnames)

    if domains:
        for name in config.list_manager.names:
            mlist = openlist(name)
            if mlist.host_name in domains:
                listnames.add(name)

    if not listnames:
        print >> sys.stderr, _('Nothing to do.')
        sys.exit(0)

    # Set the password on the lists
    if opts.password:
        shapassword = sha.new(opts.password).hexdigest()

    for listname in listnames:
        mlist = openlist(listname)
        mlist.Lock()
        try:
            if opts.password is None:
                randompw = Utils.MakeRandomPassword(
                    config.ADMIN_PASSWORD_LENGTH)
                shapassword = sha.new(randompw).hexdigest()
                notifypassword = randompw
            else:
                notifypassword = opts.password

            mlist.password = shapassword
            mlist.Save()
        finally:
            mlist.Unlock()

        # Notification
        print _('New $listname password: $notifypassword')
        if not opts.quiet:
            with i18n.using_language(mlist.preferred_language):
                hostname = mlist.host_name
                adminurl = mlist.GetScriptURL('admin', absolute=True)
                msg = Message.UserNotification(
                    mlist.owner[:], mlist.no_reply_address,
                    _('Your new $listname list password'),
                    _('''\
The site administrator at $hostname has changed the password for your
mailing list $listname.  It is now

    $notifypassword

Please be sure to use this for all future list administration.  You may want
to log in now to your list and change the password to something more to your
liking.  Visit your list admin page at

    $adminurl
'''),
                    mlist.preferred_language)
            msg.send(mlist)



if __name__ == '__main__':
    main()
