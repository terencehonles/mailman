# Copyright (C) 2008-2009 by the Free Software Foundation, Inc.
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

"""Interface for archiving schemes."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IArchiver',
    'IPipermailMailingList',
    ]


from zope.interface import Interface, Attribute
from mailman.interfaces.mailinglist import IMailingList



class IArchiver(Interface):
    """An interface to the archiver."""

    name = Attribute('The name of this archiver')

    def list_url(mlist):
        """Return the url to the top of the list's archive.

        :param mlist: The IMailingList object.
        :returns: The url string.
        """

    def permalink(mlist, message):
        """Return the url to the message in the archive.

        This url points directly to the message in the archive.  This method
        only calculates the url, it does not actually archive the message.

        :param mlist: The IMailingList object.
        :param message: The message object.
        :returns: The url string or None if the message's archive url cannot
            be calculated.
        """

    def archive_message(mlist, message):
        """Send the message to the archiver.

        :param mlist: The IMailingList object.
        :param message: The message object.
        :returns: The url string or None if the message's archive url cannot
            be calculated.
        """

    # XXX How to handle attachments?



class IPipermailMailingList(IMailingList):
    """An interface that adapts IMailingList as needed for Pipermail."""

    def archive_dir():
        """The directory for storing Pipermail artifacts.

        Pipermail expects this to be a function, not a property.
        """
