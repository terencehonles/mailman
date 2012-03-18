# Copyright (C) 2008-2012 by the Free Software Foundation, Inc.
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

"""Interface describing a pipeline handler."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'IHandler',
    ]


from zope.interface import Attribute, Interface



class IHandler(Interface):
    """A basic pipeline handler."""

    name = Attribute('Handler name; must be unique.')

    description = Attribute('A brief description of the handler.')

    def process(mlist, msg, msgdata):
        """Run the handler.

        :param mlist: The mailing list object.
        :param msg: The message object.
        :param msgdata: The message metadata.
        """
