# Copyright (C) 2010 by the Free Software Foundation, Inc.
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

"""Importing list data into Mailman 3."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Import21',
    ]


import sys
import cPickle
import datetime

from zope.component import getUtility
from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.action import Action
from mailman.interfaces.autorespond import ResponseAction
from mailman.interfaces.command import ICLISubCommand
from mailman.interfaces.digests import DigestFrequency
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.mailinglist import Personalization, ReplyToMunging
from mailman.interfaces.nntp import NewsModeration



def seconds_to_delta(value):
    return datetime.timedelta(seconds=value)


TYPES = dict(
    autorespond_owner=ResponseAction,
    autorespond_postings=ResponseAction,
    autorespond_requests=ResponseAction,
    bounce_info_stale_after=seconds_to_delta,
    bounce_you_are_disabled_warnings_interval=seconds_to_delta,
    digest_volume_frequency=DigestFrequency,
    member_moderation_action=Action,
    news_moderation=NewsModeration,
    personalize=Personalization,
    reply_goes_to_list=ReplyToMunging,
    )



class Import21:
    """Import Mailman 2.1 list data."""

    implements(ICLISubCommand)

    name = 'import21'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        self.parser = parser
        # Required positional arguments.
        command_parser.add_argument(
            'listname', metavar='LISTNAME', nargs=1,
            help=_("""\
            The 'fully qualified list name', i.e. the posting address of the
            mailing list to inject the message into."""))
        command_parser.add_argument(
            'pickle_file', metavar='FILENAME', nargs=1,
            help=_('The path to the config.pck file to import.'))

    def process(self, args):
        """See `ICLISubCommand`."""
        # Could be None or sequence of length 0.
        if args.listname is None:
            self.parser.error(_('List name is required'))
            return
        assert len(args.listname) == 1, (
            'Unexpected positional arguments: %s' % args.listname)
        fqdn_listname = args.listname[0]
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            self.parser.error(_('No such list: $fqdn_listname'))
            return
        if args.pickle_file is None:
            self.parser.error(_('config.pck file is required'))
            return
        assert len(args.pickle_file) == 1, (
            'Unexpected positional arguments: %s' % args.pickle_file)
        filename = args.pickle_file[0]
        with open(filename) as fp:
            while True:
                try:
                    config_dict = cPickle.load(fp)
                except EOFError:
                    break
                except cPickle.UnpicklingError:
                    self.parser.error(
                        _('Not a Mailman 2.1 configuration file: $filename'))
                    return
                else:
                    if not isinstance(config_dict, dict):
                        print >> sys.stderr, _(
                            'Ignoring non-dictionary: {0!r}').format(
                            config_dict)
                        continue
                    import_config(mlist, config_dict, args)
        # Commit the changes to the database.
        config.db.commit()



def import_config(mlist, config_dict, args):
    """Apply a configuration dictionary to a mailing list.

    :param mlist: The mailing list.
    :type mlist: IMailingList
    :param config_dict: The Mailman 2.1 configuration dictionary.
    :type config_dict: dict
    :param args: Command line arguments.
    """
    for key, value in config_dict.items():
        # Handle the simple case where the key is an attribute of the
        # IMailingList and the types are the same (modulo 8-bit/unicode
        # strings).
        if hasattr(mlist, key):
            if isinstance(value, str):
                value = unicode(value, 'ascii')
            # Some types require conversion.
            converter = TYPES.get(key)
            if converter is not None:
                value = converter(value)
            try:
                setattr(mlist, key, value)
            except TypeError as error:
                print >> sys.stderr, 'Type conversion error:', key
                raise
