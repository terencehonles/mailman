# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""Application level auto-reply code."""

# XXX This should undergo a rewrite to move this functionality off of the
# mailing list.  The reply governor should really apply site-wide per
# recipient (I think).

from __future__ import unicode_literals

__metaclass__ = type
__all__ = [
    'can_acknowledge',
    ]

import logging


log = logging.getLogger('mailman.vette')



def can_acknowledge(msg):
    """A boolean specifying whether this message can be acknowledged.

    There are several reasons why a message should not be acknowledged, mostly
    related to competing standards or common practices.  These include:

    * The message has a X-No-Ack header with any value
    * The message has an X-Ack header with a 'no' value
    * The message has a Precedence header
    * The message has an Auto-Submitted header and that header does not have a
      value of 'no'
    * The message has an empty Return-Path header, e.g. <>
    * The message has any RFC 2369 headers (i.e. List-* headers)

    :param msg: a Message object.
    :return: Boolean specifying whether the message can be acknowledged or not
        (which is different from whether it will be acknowledged).
    """
    # I wrote it this way for clarity and consistency with the docstring.
    for header in msg.keys():
        if header in ('x-no-ack', 'precedence'):
            return False
        if header.lower().startswith('list-'):
            return False
    if msg.get('x-ack', '').lower() == 'no':
        return False
    if msg.get('auto-submitted', 'no').lower() != 'no':
        return False
    if msg.get('return-path') == '<>':
        return False
    return True
