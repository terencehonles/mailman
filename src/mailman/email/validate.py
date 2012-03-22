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

"""Email address validation."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Validator',
    ]


import re

from zope.interface import implements

from mailman.interfaces.address import (
    IEmailValidator, InvalidEmailAddressError)
from mailman.utilities.email import split_email


# What other characters should be disallowed?
_badchars = re.compile(r'[][()<>|;^,\000-\037\177-\377]')



class Validator:
    """An email address validator."""

    implements(IEmailValidator)

    def is_valid(self, email):
        """See `IEmailValidator`."""
        if not email or ' ' in email:
            return False
        if _badchars.search(email) or email[0] == '-':
            return False
        user, domain_parts = split_email(email)
        # Local, unqualified addresses are not allowed.
        if not domain_parts:
            return False
        if len(domain_parts) < 2:
            return False
        return True

    def validate(self, email):
        """Validate an email address.

        :param address: An email address.
        :type address: string
        :raise InvalidEmailAddressError: when the address is deemed invalid.
        """
        if not self.is_valid(email):
            raise InvalidEmailAddressError(email)
