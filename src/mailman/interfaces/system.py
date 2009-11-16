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

"""System information."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ISystem',
    ]


from lazr.restful.declarations import export_as_webservice_entry, exported
from zope.interface import Interface
from zope.schema import TextLine

from mailman.core.i18n import _



class ISystem(Interface):
    """Information about the Mailman system."""

    export_as_webservice_entry()

    mailman_version = exported(TextLine(
        title=_('Mailman version'),
        description=_('The GNU Mailman version.'),
        ))

    python_version = exported(TextLine(
        title=_('Python version'),
        description=_('The Python version.'),
        ))
