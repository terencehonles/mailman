# Copyright (C) 2009 by the Free Software Foundation, Inc.
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
    ]


from zope.interface import implements

from mailman.Utils import maketext
from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.constants import system_preferences
from mailman.core.errors import InvalidEmailAddress
from mailman.email.message import UserNotification
from mailman.i18n import _, using_language
from mailman.interfaces.command import ICLISubCommand
from mailman.interfaces.domain import (
    BadDomainSpecificationError, IDomainManager)
from mailman.interfaces.listmanager import ListAlreadyExistsError



class Lists:
    """The `lists` subcommand."""

    implements(ICLISubCommand)

    def add(self, parser, subparser):
        """See `ICLISubCommand`."""
        lists_parser = subparser.add_parser(
            'lists', help=_('List all mailing lists'))
        lists_parser.set_defaults(func=self.process)
        lists_parser.add_argument(
            '-a', '--advertised',
            default=False, action='store_true',
            help=_(
                'List only those mailing lists that are publicly advertised'))
        lists_parser.add_argument(
            '-b', '--bare',
            default=False, action='store_true',
            help=_('Show only the list name, with no description'))
        lists_parser.add_argument(
            '-d', '--domain',
            action='append', help=_("""\
            List only those mailing lists hosted on the given domain, which
            must be the email host name.  Multiple -d options may be given.
            """))
        lists_parser.add_argument(
            '-f', '--full',
            default=False, action='store_true',
            help=_(
                'Show the full mailing list name (i.e. the posting address'))

    def process(self, args):
        """See `ICLISubCommand`."""
        mailing_lists = []
        list_manager = config.db.list_manager
        # Gather the matching mailing lists.
        for fqdn_name in sorted(list_manager.names):
            mlist = list_manager.get(fqdn_name)
            if args.advertised and not mlist.advertised:
                continue
            domains = getattr(args, 'domains', None)
            if domains and mlist.host_name not in domains:
                continue
            mailing_lists.append(mlist)
        # Maybe no mailing lists matched.
        if len(mailing_lists) == 0:
            if not args.bare:
                print _('No matching mailing lists found')
            return
        if not args.bare:
            count = len(mailing_lists)
            print _('$count matching mailing lists found:')
        # Calculate the longest mailing list name.
        longest = len(
            max(mlist.fqdn_listname for mlist in mailing_lists)
            if args.full else
            max(mlist.real_name for mlist in mailing_lists))
        # Print it out.
        for mlist in mailing_lists:
            name = (mlist.fqdn_listname if args.full else mlist.real_name)
            if args.bare:
                print name
            else:
                description = (mlist.description
                               if mlist.description is not None
                               else _('[no description available]'))
                print '{0:{2}} - {1:{3}}'.format(
                    name, description, longest, 77 - longest)



class Create:
    """The `create` subcommand."""

    implements(ICLISubCommand)

    def add(self, parser, subparser):
        """See `ICLISubCommand`."""
        self.parser = parser
        create_parser = subparser.add_parser(
            'create', help=_('Create a mailing list'))
        create_parser.set_defaults(func=self.process)
        create_parser.add_argument(
            '--language',
            type='unicode', metavar='CODE', help=_("""\
            Set the list's preferred language to CODE, which must be a
            registered two letter language code."""))
        create_parser.add_argument(
            '-o', '--owner',
            type='unicode', action='append', default=[],
            dest='owners', metavar='OWNER', help=_("""\
            Specify a listowner email address.  If the address is not
            currently registered with Mailman, the address is registered and
            linked to a user.  Mailman will send a confirmation message to the
            address, but it will also send a list creation notice to the
            address.  More than one owner can be specified."""))
        create_parser.add_argument(
            '-n', '--notify',
            default=False, action='store_true',
            help=_("""\
            Notify the list owner by email that their mailing list has been
            created."""))
        create_parser.add_argument(
            '-q', '--quiet',
            default=False, action='store_true',
            help=_('Print less output.'))
        create_parser.add_argument(
            '-d', '--domain',
            default=False, action='store_true',
            help=_("""\
            Register the mailing list's domain if not yet registered."""))
        # Required positional argument.
        create_parser.add_argument(
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
        if language_code not in config.languages.codes:
            self.parser.error(_('Invalid language code: $language_code'))
            return
        assert len(args.listname) == 1, (
            'Unexpected positional arguments: %s' % args.listname)
        # Check to see if the domain exists or not.
        fqdn_listname = args.listname[0]
        listname, at, domain = fqdn_listname.partition('@')
        domain_mgr = IDomainManager(config)
        if domain_mgr.get(domain) is None and args.domain:
            domain_mgr.add(domain)
        try:
            mlist = create_list(fqdn_listname, args.owners)
        except InvalidEmailAddress:
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
        mlist.preferred_language = config.languages[language_code]
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
            text = maketext('newlist.txt', d, mlist=mlist)
            # Set the I18N language to the list's preferred language so the
            # header will match the template language.  Stashing and restoring
            # the old translation context is just (healthy? :) paranoia.
            with using_language(mlist.preferred_language.code):
                msg = UserNotification(
                    owner_mail, mlist.no_reply_address,
                    _('Your new mailing list: $fqdn_listname'),
                    text, mlist.preferred_language)
                msg.send(mlist)
