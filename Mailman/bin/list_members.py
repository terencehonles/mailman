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

import sys
import optparse

from email.Utils import formataddr

from Mailman import Errors
from Mailman import MailList
from Mailman import MemberAdaptor
from Mailman import Utils
from Mailman import Version
from Mailman.configuration import config
from Mailman.i18n import _

__i18n_templates__ = True

ENC = sys.getdefaultencoding()
COMMASPACE = ', '

WHYCHOICES = {
    'enabled' : MemberAdaptor.ENABLED,
    'unknown' : MemberAdaptor.UNKNOWN,
    'byuser'  : MemberAdaptor.BYUSER,
    'byadmin' : MemberAdaptor.BYADMIN,
    'bybounce': MemberAdaptor.BYBOUNCE,
    }

KINDCHOICES = set(('mime', 'plain', 'any'))



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] listname

List all the members of a mailing list.  Note that with the options below, if
neither -r or -d is supplied, regular members are printed first, followed by
digest members, but no indication is given as to address status.

listname is the name of the mailing list to use."""))
    parser.add_option('-o', '--output',
                      type='string', help=_("""\
Write output to specified file instead of standard out."""))
    parser.add_option('-r', '--regular',
                      default=None, action='store_true',
                      help=_('Print just the regular (non-digest) members.'))
    parser.add_option('-d', '--digest',
                      default=None, type='string', metavar='KIND',
                      help=_("""\
Print just the digest members.  KIND can be 'mime', 'plain', or
'any'.  'mime' prints just the members receiving MIME digests, while 'plain'
prints just the members receiving plain text digests.  'any' prints all
members receiving any kind of digest."""))
    parser.add_option('-n', '--nomail',
                      type='string', metavar='WHY', help=_("""\
Print the members that have delivery disabled.  WHY selects just the subset of
members with delivery disabled for a particular reason, where 'any' prints all
disabled members.  'byadmin', 'byuser', 'bybounce', and 'unknown' prints just
the users who are disabled for that particular reason.  WHY can also be
'enabled' which prints just those members for whom delivery is enabled."""))
    parser.add_option('-f', '--fullnames',
                      default=False, action='store_true',
                      help=_('Include the full names in the output'))
    parser.add_option('-p', '--preserve',
                      default=False, action='store_true', help=_("""\
Output member addresses case preserved the way they were added to the list.
Otherwise, addresses are printed in all lowercase."""))
    parser.add_option('-i', '--invalid',
                      default=False, action='store_true', help=_("""\
Print only the addresses in the membership list that are invalid.  Ignores -r,
-d, -n."""))
    parser.add_option('-u', '--unicode',
                      default=False, action='store_true', help=_("""\
Print addresses which are stored as Unicode objects instead of normal string
objects.  Ignores -r, -d, -n."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if not args:
        parser.print_help()
        print >> sys.stderr, _('Missing listname')
        sys.exit(1)
    if len(args) > 1:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    if opts.digest is not None:
        opts.kind = opts.digest.lower()
        if opts.kind not in KINDCHOICES:
            parser.print_help()
            print >> sys.stderr, _('Invalid value for -d: $opts.digest')
            sys.exit(1)
    if opts.nomail is not None:
        why = opts.nomail.lower()
        if why == 'any':
            opts.why = 'any'
        elif why not in WHYCHOICES:
            parser.print_help()
            print >> sys.stderr, _('Invalid value for -n: $opts.nomail')
            sys.exit(1)
        opts.why = why
    if opts.regular is None and opts.digest is None:
        opts.regular = opts.digest = True
        opts.kind = 'any'
    return parser, opts, args



def isunicode(s):
    return isinstance(s, unicode)


def safe(s):
    if not s:
        return ''
    if isunicode(s):
        return s.encode(ENC, 'replace')
    return unicode(s, ENC, 'replace').encode(ENC, 'replace')


def isinvalid(addr):
    try:
        Utils.ValidateEmail(addr)
        return False
    except Errors.EmailAddressError:
        return True



def whymatches(mlist, addr, why):
    # Return true if the `why' matches the reason the address is enabled, or
    # in the case of why is None, that they are disabled for any reason
    # (i.e. not enabled).
    status = mlist.getDeliveryStatus(addr)
    if why in (None, 'any'):
        return status <> MemberAdaptor.ENABLED
    return status == WHYCHOICES[why]



def main():
    parser, opts, args = parseargs()
    config.load(opts.config)

    listname = args[0].lower().strip()
    if opts.output:
        try:
            fp = open(opts.output, 'w')
        except IOError:
            print >> sys.stderr, _(
                'Could not open file for writing: $opts.output')
            sys.exit(1)
    else:
        fp = sys.stdout

    try:
        mlist = MailList.MailList(listname, lock=False)
    except Errors.MMListError:
        print >> sys.stderr, _('No such list: $listname')
        sys.exit(1)

    # Get the lowercased member addresses
    rmembers = mlist.getRegularMemberKeys()
    dmembers = mlist.getDigestMemberKeys()

    if opts.preserve:
        # Convert to the case preserved addresses
        rmembers = mlist.getMemberCPAddresses(rmembers)
        dmembers = mlist.getMemberCPAddresses(dmembers)

    if opts.invalid or opts.unicode:
        all = rmembers + dmembers
        all.sort()
        for addr in all:
            name = opts.fullnames and mlist.getMemberName(addr) or ''
            showit = False
            if opts.invalid and isinvalid(addr):
                showit = True
            if opts.unicode and isunicode(addr):
                showit = True
            if showit:
                print >> fp, formataddr((safe(name), addr))
        return
    if opts.regular:
        rmembers.sort()
        for addr in rmembers:
            name = opts.fullnames and mlist.getMemberName(addr) or ''
            # Filter out nomails
            if opts.nomail and not whymatches(mlist, addr, opts.why):
                continue
            print >> fp, formataddr((safe(name), addr))
    if opts.digest:
        dmembers.sort()
        for addr in dmembers:
            name = opts.fullnames and mlist.getMemberName(addr) or ''
            # Filter out nomails
            if opts.nomail and not whymatches(mlist, addr, opts.why):
                continue
            # Filter out digest kinds
            if mlist.getMemberOption(addr, config.DisableMime):
                # They're getting plain text digests
                if opts.kind == 'mime':
                    continue
            else:
                # They're getting MIME digests
                if opts.kind == 'plain':
                    continue
            print >> fp, formataddr((safe(name), addr))



if __name__ == '__main__':
    main()
