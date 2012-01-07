# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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

"""Base Mailman exceptions.

The exceptions in this module are those that are commonly shared among many
components.  More specific exceptions will be located in the relevant
interfaces.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'MailmanError',
    ]



class MailmanError(Exception):
    """Base class for all Mailman exceptions."""
