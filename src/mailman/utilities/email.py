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

"""Email helpers."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'add_message_hash',
    'split_email',
    ]


from base64 import b32encode
from hashlib import sha1




def split_email(address):
    """Split an email address into a user name and domain.

    :param address: An email address.
    :type address: string
    :return: The user name and domain split on dots.
    :rtype: 2-tuple where the first item is the local part and the second item
        is a sequence of domain parts.
    """
    local_part, at, domain = address.partition('@')
    if len(at) == 0:
        # There was no at-sign in the email address.
        return local_part, None
    return local_part, domain.split('.')


def add_message_hash(msg):
    """Add a X-Message-ID-Hash header derived from Message-ID.

    This function works by side-effect; the original message is mutated.  Any
    existing X-Message-ID-Headers are deleted if a Message-ID header is
    found.  If no Message-ID header is found, the original message is not
    modified.

    :param msg: An email message
    :type msg: `email.message.Message` or derived
    """
    message_id = msg.get('message-id')
    if message_id is None:
        return
    # The angle brackets are not part of the Message-ID.  See RFC 2822
    # and http://wiki.list.org/display/DEV/Stable+URLs
    if message_id.startswith('<') and message_id.endswith('>'):
        message_id = message_id[1:-1]
    else:
        message_id = message_id.strip()
    digest = sha1(message_id).digest()
    message_id_hash = b32encode(digest)
    del msg['x-message-id-hash']
    msg['X-Message-ID-Hash'] = message_id_hash
