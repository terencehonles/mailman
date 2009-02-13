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

"""Module stuff."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'is_valid',
    'validate',
    ]


import re

from mailman.core.errors import InvalidEmailAddress
from mailman.email.utils import split_email


# What other characters should be disallowed?
_badchars = re.compile(r'[][()<>|;^,\000-\037\177-\377]')



def validate(address):
    """Validate an email address.

    :param address: An email address.
    :type address: string
    :raise `InvalidEmailAddress`: when the address is deemed invalid.
    """
    if not is_valid(address):
        raise InvalidEmailAddress(repr(address))



def is_valid(address):
    """Check if an email address if valid.

    :param address: An email address.
    :type address: string
    :return: A flag indicating whether the email address is okay or not.
    :rtype: bool
    """
    if not address or ' ' in address:
        return False
    if _badchars.search(address) or address[0] == '-':
        return False
    user, domain_parts = split_email(address)
    # Local, unqualified addresses are not allowed.
    if not domain_parts:
        return False
    if len(domain_parts) < 2:
        return False
    return True
