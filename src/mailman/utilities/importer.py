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

"""Importer routines."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'import_config_pck',
    ]


import cPickle
import datetime

from mailman.interfaces.action import Action
from mailman.interfaces.autorespond import ResponseAction
from mailman.interfaces.digests import DigestFrequency
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



def import_config_pck(mlist, config_dict):
    """Apply a config.pck configuration dictionary to a mailing list.

    :param mlist: The mailing list.
    :type mlist: IMailingList
    :param config_dict: The Mailman 2.1 configuration dictionary.
    :type config_dict: dict
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