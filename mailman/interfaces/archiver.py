# Copyright (C) 2008 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Interface for archiving schemes."""

from zope.interface import Interface, Attribute



class IArchiver(Interface):
    """An interface to the archiver."""

    def get_list_url(mlist):
        """Return the url to the top of the list's archive.

        :param mlist: The IMailingList object.
        :returns: The url string.
        """

    def get_message_url(mlist, message):
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

        This uses `get_message_url()` to calculate and return the url to the
        message in the archives.

        :param mlist: The IMailingList object.
        :param message: The message object.
        :returns: The url string or None if the message's archive url cannot
            be calculated.
        """

    # XXX How to handle attachments?
