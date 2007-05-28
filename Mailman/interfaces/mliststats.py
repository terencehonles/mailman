# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

"""Interface for various mailing list statistics."""

from zope.interface import Interface, Attribute



class IMailingListStatistics(Interface):
    """Various statistics of a mailing list."""

    creation_date = Attribute(
        """The date and time that the mailing list was created.""")

    last_post_date = Attribute(
        """The date and time a message was last posted to the mailing list.""")

    post_number = Attribute(
        """A monotonically increasing integer sequentially assigned to each
        list posting.""")

    last_digest_date = Attribute(
        """The date and time a digest of this mailing list was last sent.""")
