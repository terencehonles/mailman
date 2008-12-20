# Copyright (C) 2008 by the Free Software Foundation, Inc.
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

"""Configuration helpers."""

__metaclass__ = type
__all__ = [
    'as_boolean',
    'as_log_level',
    ]


import logging



def as_boolean(value):
    """Turn a string into a boolean.

    :param value: A string with one of the following values
        (case-insensitive): true, yes, 1, on, enable, enabled (for True), or
        false, no, 0, off, disable, disabled (for False).  Everything else is
        an error.
    :type value: string
    :return: True or False.
    :rtype: boolean
    """
    value = value.lower()
    if value in ('true', 'yes', '1', 'on', 'enabled', 'enable'):
        return True
    if value in ('false', 'no', '0', 'off', 'disabled', 'disable'):
        return False
    raise ValueError('Invalid boolean value: %s' % value)



def as_log_level(value):
    """Turn a string into a log level.
    
    :param value: A string with a value (case-insensitive) equal to one of the
        symbolic logging levels.
    :type value: string
    :return: A logging level constant.
    :rtype: int
    """
    value = value.upper()
    return getattr(logging, value)
