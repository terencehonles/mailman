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

"""String utilities."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'expand'
    ]


import logging
from string import Template

log = logging.getLogger('mailman.error')



def expand(template, substitutions, template_class=Template):
    """Expand string template with substitutions.

    :param template: A PEP 292 $-string template.
    :type template: string
    :param substitutions: The substitutions dictionary.
    :type substitutions: dict
    :param template_class: The template class to use.
    :type template_class: class
    :return: The substituted string.
    :rtype: string
    """
    # Python 2.6 requires ** dictionaries to have str, not unicode keys, so
    # convert as necessary.  Note that string.Template uses **.  For our
    # purposes, keys should always be ascii.  Values though can be anything.
    cooked = substitutions.__class__()
    for key in substitutions:
        if isinstance(key, unicode):
            key = key.encode('ascii')
        cooked[key] = substitutions[key]
    try:
        return template_class(template).safe_substitute(cooked)
    except (TypeError, ValueError):
        # The template is really screwed up.
        log.exception('broken template: %s', template)
