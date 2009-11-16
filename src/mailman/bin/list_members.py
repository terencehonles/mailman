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

import sys

from email.Utils import formataddr
from zope.component import getUtility

from mailman.core import errors
from mailman.core.i18n import _
from mailman.email.validate import is_valid
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.members import DeliveryStatus
from mailman.interfaces.usermanager import IUserManager
from mailman.options import SingleMailingListOptions


COMMASPACE = ', '

WHYCHOICES = {
    'enabled' : DeliveryStatus.enabled,
    'byuser'  : DeliveryStatus.by_user,
    'byadmin' : DeliveryStatus.by_moderator,
    'bybounce': DeliveryStatus.by_bounces,
    }

KINDCHOICES = set(('mime', 'plain', 'any'))



class ScriptOptions(SingleMailingListOptions):
    usage = _("""\
%prog [options]

List all the members of a mailing list.  Note that with the options below, if
neither -r or -d is supplied, regular members are printed first, followed by
digest members, but no indication is given as to address status.

listname is the name of the mailing list to use.""")

    def add_options(self):
        super(ScriptOptions, self).add_options()
        self.parser.add_option(
            '-o', '--output',
            type='string', help=_("""\
Write output to specified file instead of standard out."""))
        self.parser.add_option(
            '-r', '--regular',
            default=None, action='store_true',
            help=_('Print just the regular (non-digest) members.'))
        self.parser.add_option(
            '-d', '--digest',
            default=None, type='string', metavar='KIND',
            help=_("""\
Print just the digest members.  KIND can be 'mime', 'plain', or
'any'.  'mime' prints just the members receiving MIME digests, while 'plain'
prints just the members receiving plain text digests.  'any' prints all
members receiving any kind of digest."""))
        self.parser.add_option(
            '-n', '--nomail',
            type='string', metavar='WHY', help=_("""\
Print the members that have delivery disabled.  WHY selects just the subset of
members with delivery disabled for a particular reason, where 'any' prints all
disabled members.  'byadmin', 'byuser', 'bybounce', and 'unknown' prints just
the users who are disabled for that particular reason.  WHY can also be
'enabled' which prints just those members for whom delivery is enabled."""))
        self.parser.add_option(
            '-f', '--fullnames',
            default=False, action='store_true',
            help=_('Include the full names in the output'))
        self.parser.add_option(
            '-i', '--invalid',
            default=False, action='store_true', help=_("""\
Print only the addresses in the membership list that are invalid.  Ignores -r,
-d, -n."""))

    def sanity_check(self):
        if not self.options.listname:
            self.parser.error(_('Missing listname'))
        if len(self.arguments) > 0:
            self.parser.print_error(_('Unexpected arguments'))
        if self.options.digest is not None:
            self.options.kind = self.options.digest.lower()
            if self.options.kind not in KINDCHOICES:
                self.parser.error(
                    _('Invalid value for -d: $self.options.digest'))
        if self.options.nomail is not None:
            why = self.options.nomail.lower()
            if why == 'any':
                self.options.why = 'any'
            elif why not in WHYCHOICES:
                self.parser.error(
                    _('Invalid value for -n: $self.options.nomail'))
            self.options.why = why
        if self.options.regular is None and self.options.digest is None:
            self.options.regular = self.options.digest = True
            self.options.kind = 'any'



def safe(string):
    if not string:
        return ''
    return string.encode(sys.getdefaultencoding(), 'replace')



def whymatches(mlist, addr, why):
    # Return true if the `why' matches the reason the address is enabled, or
    # in the case of why is None, that they are disabled for any reason
    # (i.e. not enabled).
    status = mlist.getDeliveryStatus(addr)
    if why in (None, 'any'):
        return status <> DeliveryStatus.enabled
    return status == WHYCHOICES[why]



def main():
    options = ScriptOptions()
    options.initialize()

    fqdn_listname = options.options.listname
    if options.options.output:
        try:
            fp = open(options.output, 'w')
        except IOError:
            options.parser.error(
                _('Could not open file for writing: $options.options.output'))
    else:
        fp = sys.stdout

    mlist = getUtility(IListManager).get(fqdn_listname)
    if mlist is None:
        options.parser.error(_('No such list: $fqdn_listname'))

    # The regular delivery and digest members.
    rmembers = set(mlist.regular_members.members)
    dmembers = set(mlist.digest_members.members)

    fullnames = options.options.fullnames
    user_manager = getUtility(IUserManager)
    if options.options.invalid:
        all = sorted(member.address.address for member in rmembers + dmembers)
        for address in all:
            user = user_manager.get_user(address)
            name = (user.real_name if fullnames and user else u'')
            if options.options.invalid and not is_valid(address):
                print >> fp, formataddr((safe(name), address))
        return
    if options.options.regular:
        for address in sorted(member.address.address for member in rmembers):
            user = user_manager.get_user(address)
            name = (user.real_name if fullnames and user else u'')
            # Filter out nomails
            if (options.options.nomail and
                not whymatches(mlist, address, options.options.why)):
                continue
            print >> fp, formataddr((safe(name), address))
    if options.options.digest:
        for address in sorted(member.address.address for member in dmembers):
            user = user_manager.get_user(address)
            name = (user.real_name if fullnames and user else u'')
            # Filter out nomails
            if (options.options.nomail and
                not whymatches(mlist, address, options.options.why)):
                continue
            # Filter out digest kinds
##             if mlist.getMemberOption(addr, config.DisableMime):
##                 # They're getting plain text digests
##                 if opts.kind == 'mime':
##                     continue
##             else:
##                 # They're getting MIME digests
##                 if opts.kind == 'plain':
##                     continue
            print >> fp, formataddr((safe(name), address))



if __name__ == '__main__':
    main()
