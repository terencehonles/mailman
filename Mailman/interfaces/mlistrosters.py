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

"""Interface for mailing list rosters and roster sets."""

from zope.interface import Interface, Attribute



class IMailingListRosters(Interface):
    """Mailing list rosters, roster sets, and members.

    This are all the email addresses that might possibly get messages from or
    relating to this mailing list.
    """

    owners = Attribute(
        """The IUser owners of this mailing list.

        This does not include the IUsers who are moderators but not owners of
        the mailing list.""")

    moderators = Attribute(
        """The IUser moderators of this mailing list.

        This does not include the IUsers who are owners but not moderators of
        the mailing list.""")

    administrators = Attribute(
        """The IUser administrators of this mailing list.

        This includes the IUsers who are both owners and moderators of the
        mailing list.""")

    members = Attribute(
        """An iterator over all the members of the mailing list, regardless of
        whether they are to receive regular messages or digests, or whether
        they have their delivery disabled or not.""")

    regular_members = Attribute(
        """An iterator over all the IMembers who are to receive regular
        postings (i.e. non-digests) from the mailing list, regardless of
        whether they have their delivery disabled or not.""")

    digest_members = Attribute(
        """An iterator over all the IMembers who are to receive digests of
        postings to this mailing list, regardless of whether they have their
        deliver disabled or not, or of the type of digest they are to
        receive.""")
