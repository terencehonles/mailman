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

"""Interface for a mailing list identity."""

from zope.interface import Interface, Attribute



class IMailingListIdentity(Interface):
    """The basic identifying information of a mailing list."""

    list_name = Attribute(
        """The read-only short name of the mailing list.  Note that where a
        Mailman installation supports multiple domains, this short name may
        not be unique.  Use the fqdn_listname attribute for a guaranteed
        unique id for the mailing list.  This short name is always the local
        part of the posting email address.  For example, if messages are
        posted to mylist@example.com, then the list_name is 'mylist'.""")

    host_name = Attribute(
        """The read-only domain name 'hosting' this mailing list.  This is
        always the domain name part of the posting email address, and it may
        bear no relationship to the web url used to access this mailing list.
        For example, if messages are posted to mylist@example.com, then the
        host_name is 'example.com'.""")

    fqdn_listname = Attribute(
        """The read-only fully qualified name of the mailing list.  This is
        the guaranteed unique id for the mailing list, and it is always the
        address to which messages are posted, e.g. mylist@example.com.  It is
        always comprised of the list_name + '@' + host_name.""")
