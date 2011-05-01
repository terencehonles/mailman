# Copyright (C) 2009-2011 by the Free Software Foundation, Inc.
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
    'split_email',
    ]


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
