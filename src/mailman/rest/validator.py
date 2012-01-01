# Copyright (C) 2010-2012 by the Free Software Foundation, Inc.
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

"""REST web form validation."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Validator',
    'enum_validator',
    'language_validator',
    'subscriber_validator',
    ]


from uuid import UUID
from zope.component import getUtility

from mailman.interfaces.languages import ILanguageManager


COMMASPACE = ', '



class enum_validator:
    """Convert an enum value name into an enum value."""

    def __init__(self, enum_class):
        self._enum_class = enum_class

    def __call__(self, enum_value):
        # This will raise a ValueError if the enum value is unknown.  Let that
        # percolate up.
        return self._enum_class[enum_value]


def subscriber_validator(subscriber):
    """Convert an email-or-int to an email-or-UUID."""
    try:
        return UUID(int=int(subscriber))
    except ValueError:
        return subscriber


def language_validator(code):
    """Convert a language code to a Language object."""
    return getUtility(ILanguageManager)[code]



class Validator:
    """A validator of parameter input."""

    def __init__(self, **kws):
        if '_optional' in kws:
            self._optional = set(kws.pop('_optional'))
        else:
            self._optional = set()
        self._converters = kws.copy()

    def __call__(self, request):
        values = {}
        extras = set()
        cannot_convert = set()
        form_data = {}
        # All keys which show up only once in the form data get a scalar value
        # in the pre-converted dictionary.  All keys which show up more than
        # once get a list value.
        missing = object()
        # This is a gross hack to allow PATCH.  See helpers.py for details.
        try:
            items = request.PATCH.items()
        except AttributeError:
            items = request.POST.items()
        for key, new_value in items:
            old_value = form_data.get(key, missing)
            if old_value is missing:
                form_data[key] = new_value
            elif isinstance(old_value, list):
                old_value.append(new_value)
            else:
                form_data[key] = [old_value, new_value]
        # Now do all the conversions.
        for key, value in form_data.items():
            try:
                values[key] = self._converters[key](value)
            except KeyError:
                extras.add(key)
            except (TypeError, ValueError):
                cannot_convert.add(key)
        # Make sure there are no unexpected values.
        if len(extras) != 0:
            extras = COMMASPACE.join(sorted(extras))
            raise ValueError('Unexpected parameters: {0}'.format(extras))
        # Make sure everything could be converted.
        if len(cannot_convert) != 0:
            bad = COMMASPACE.join(sorted(cannot_convert))
            raise ValueError('Cannot convert parameters: {0}'.format(bad))
        # Make sure nothing's missing.
        value_keys = set(values)
        required_keys = set(self._converters) - self._optional
        if value_keys & required_keys != required_keys:
            missing = COMMASPACE.join(sorted(required_keys - value_keys))
            raise ValueError('Missing parameters: {0}'.format(missing))
        return values
