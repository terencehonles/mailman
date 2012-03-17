# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""The 'lists' subcommand."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Create',
    'Lists',
    'Remove',
    ]


from zope.component import getUtility
from zope.interface import implements

from mailman.app.lifecycle import create_list, remove_list
from mailman.config import config
from mailman.core.constants import system_preferences
from mailman.core.i18n import _
from mailman.email.message import UserNotification
from mailman.interfaces.address import (
    IEmailValidator, InvalidEmailAddressError)
from mailman.interfaces.command import ICLISubCommand
from mailman.interfaces.domain import (
    BadDomainSpecificationError, IDomainManager)
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.listmanager import IListManager, ListAlreadyExistsError
from mailman.utilities.i18n import make


COMMASPACE = ', '



class Lists:
    """List all mailing lists"""

    implements(ICLISubCommand)

    name = 'lists'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        command_parser.add_argument(
            '-a', '--advertised',
            default=False, action='store_true',
            help=_(
                'List only those mailing lists that are publicly advertised'))
        command_parser.add_argument(
            '-n', '--names',
            default=False, action='store_true',
            help=_('Show also the list names'))
        command_parser.add_argument(
            '-d', '--descriptions',
            default=False, action='store_true',
            help=_('Show also the list descriptions'))
        command_parser.add_argument(
            '-q', '--quiet',
            default=False, action='store_true',
            help=_('Less verbosity'))
        command_parser.add_argument(
            '--domain',
            action='append', help=_("""\
            List only those mailing lists hosted on the given domain, which
            must be the email host name.  Multiple -d options may be given.
            """))

    def process(self, args):
        """See `ICLISubCommand`."""
        mailing_lists = []
        list_manager = getUtility(IListManager)
        # Gather the matching mailing lists.
        for fqdn_name in sorted(list_manager.names):
            mlist = list_manager.get(fqdn_name)
            if args.advertised and not mlist.advertised:
                continue
            domains = getattr(args, 'domains', None)
            if domains and mlist.mail_host not in domains:
                continue
            mailing_lists.append(mlist)
        # Maybe no mailing lists matched.
        if len(mailing_lists) == 0:
            if not args.quiet:
                print _('No matching mailing lists found')
            return
        count = len(mailing_lists)
        if not args.quiet:
            print _('$count matching mailing lists found:')
        # Calculate the longest identifier.
        longest = 0
        output = []
        for mlist in mailing_lists:
            if args.names:
                identifier = '{0} [{1}]'.format(
                    mlist.fqdn_listname, mlist.display_name)
            else:
                identifier = mlist.fqdn_listname
            longest = max(len(identifier), longest)
            output.append((identifier, mlist.description))
        # Print it out.
        if args.descriptions:
            format_string = '{0:{2}} - {1:{3}}'
        else:
            format_string = '{0:{2}}'
        for identifier, description in output:
            print format_string.format(
                identifier, description, longest, 70 - longest)



class Create:
    """Create a mailing list"""

    implements(ICLISubCommand)

    name = 'create'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        self.parser = parser
        command_parser.add_argument(
            '--language',
            type=unicode, metavar='CODE', help=_("""\
            Set the list's preferred language to CODE, which must be a
            registered two letter language code."""))
        command_parser.add_argument(
            '-o', '--owner',
            type=unicode, action='append', default=[],
            dest='owners', metavar='OWNER', help=_("""\
            Specify a listowner email address.  If the address is not
            currently registered with Mailman, the address is registered and
            linked to a user.  Mailman will send a confirmation message to the
            address, but it will also send a list creation notice to the
            address.  More than one owner can be specified."""))
        command_parser.add_argument(
            '-n', '--notify',
            default=False, action='store_true',
            help=_("""\
            Notify the list owner by email that their mailing list has been
            created."""))
        command_parser.add_argument(
            '-q', '--quiet',
            default=False, action='store_true',
            help=_('Print less output.'))
        command_parser.add_argument(
            '-d', '--domain',
            default=False, action='store_true',
            help=_("""\
            Register the mailing list's domain if not yet registered."""))
        # Required positional argument.
        command_parser.add_argument(
            'listname', metavar='LISTNAME', nargs=1,
            help=_("""\
            The 'fully qualified list name', i.e. the posting address of the
            mailing list.  It must be a valid email address and the domain
            must be registered with Mailman.  List names are forced to lower
            case."""))

    def process(self, args):
        """See `ICLISubCommand`."""
        language_code = (args.language
                         if args.language is not None
                         else system_preferences.preferred_language.code)
        # Make sure that the selected language code is known.
        if language_code not in getUtility(ILanguageManager).codes:
            self.parser.error(_('Invalid language code: $language_code'))
            return
        assert len(args.listname) == 1, (
            'Unexpected positional arguments: %s' % args.listname)
        # Check to see if the domain exists or not.
        fqdn_listname = args.listname[0]
        listname, at, domain = fqdn_listname.partition('@')
        domain_manager = getUtility(IDomainManager)
        if domain_manager.get(domain) is None and args.domain:
            domain_manager.add(domain)
        # Validate the owner email addresses.  The problem with doing this
        # check in create_list() is that you wouldn't be able to distinguish
        # between an InvalidEmailAddressError for the list name or the
        # owners.  I suppose we could subclass that exception though.
        if args.owners:
            validator = getUtility(IEmailValidator)
            invalid_owners = [owner for owner in args.owners
                              if not validator.is_valid(owner)]
            if invalid_owners:
                invalid = COMMASPACE.join(sorted(invalid_owners))
                self.parser.error(_('Illegal owner addresses: $invalid'))
                return
        try:
            mlist = create_list(fqdn_listname, args.owners)
        except InvalidEmailAddressError:
            self.parser.error(_('Illegal list name: $fqdn_listname'))
            return
        except ListAlreadyExistsError:
            self.parser.error(_('List already exists: $fqdn_listname'))
            return
        except BadDomainSpecificationError, domain:
            self.parser.error(_('Undefined domain: $domain'))
            return
        # Find the language associated with the code, then set the mailing
        # list's preferred language to that.  The changes then must be
        # committed to the database.
        mlist.preferred_language = getUtility(ILanguageManager)[language_code]
        config.db.commit()
        # Do the notification.
        if not args.quiet:
            print _('Created mailing list: $mlist.fqdn_listname')
        if args.notify:
            d = dict(
                listname        = mlist.fqdn_listname,
                admin_url       = mlist.script_url('admin'),
                listinfo_url    = mlist.script_url('listinfo'),
                requestaddr     = mlist.request_address,
                siteowner       = mlist.no_reply_address,
                )
            text = make('newlist.txt', mailing_list=mlist, **d)
            # Set the I18N language to the list's preferred language so the
            # header will match the template language.  Stashing and restoring
            # the old translation context is just (healthy? :) paranoia.
            with _.using(mlist.preferred_language.code):
                msg = UserNotification(
                    args.owners, mlist.no_reply_address,
                    _('Your new mailing list: $fqdn_listname'),
                    text, mlist.preferred_language)
                msg.send(mlist)



class Remove:
    """Remove a mailing list"""

    implements(ICLISubCommand)

    name = 'remove'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        command_parser.add_argument(
            '-q', '--quiet',
            default=False, action='store_true',
            help=_('Suppress status messages'))
        # Required positional argument.
        command_parser.add_argument(
            'listname', metavar='LISTNAME', nargs=1,
            help=_("""\
            The 'fully qualified list name', i.e. the posting address of the
            mailing list."""))

    def process(self, args):
        """See `ICLISubCommand`."""
        def log(message):
            if not args.quiet:
                print message
        assert len(args.listname) == 1, (
            'Unexpected positional arguments: %s' % args.listname)
        fqdn_listname = args.listname[0]
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            log(_('No such list: $fqdn_listname'))
            return
        else:
            log(_('Removed list: $fqdn_listname'))
        remove_list(fqdn_listname, mlist)
        config.db.commit()
