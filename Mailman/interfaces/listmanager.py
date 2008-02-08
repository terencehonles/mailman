# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""Interface for list storage, deleting, and finding."""

from zope.interface import Interface, Attribute



class IListManager(Interface):
    """The interface of the global list manager.

    The list manager manages IMailingList objects.  You can add and remove
    IMailingList objects from the list manager, and you can retrieve them
    from the manager via their fully qualified list name
    (e.g. 'mylist@example.com').
    """

    def create(fqdn_listname):
        """Create an IMailingList with the given fully qualified list name.

        Raises MMListAlreadyExistsError if the named list already exists.
        """

    def get(fqdn_listname):
        """Return the IMailingList with the given fully qualified list name.

        Raises MMUnknownListError if the names list does not exist.
        """

    def delete(mlist):
        """Remove the IMailingList from the backend storage."""

    def get(fqdn_listname):
        """Find the IMailingList with the matching fully qualified list name.

        :param fqdn_listname: Fully qualified list name to get.
        :return: The matching IMailingList or None if there was no such
            matching mailing list.
        """

    mailing_lists = Attribute(
        """An iterator over all the IMailingList objects managed by this list
        manager.""")

    names = Attribute(
        """An iterator over the fully qualified list names of all mailing
        lists managed by this list manager.""")
