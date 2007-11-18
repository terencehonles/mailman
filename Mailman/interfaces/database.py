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

"""Interfaces for database interaction.

By providing an object with this interface and declaring it in a package
setup.py file as an entry point in the 'mailman.database' group with the name
'initializer', you can distribute entirely different database layers for
Mailman's back end.
"""

from zope.interface import Interface, Attribute



class IDatabase(Interface):
    """Database layer interface."""

    def initialize(debug=None):
        """Initialize the database layer, using whatever means necessary.

        :param debug: When None (the default), the configuration file
            determines whether the database layer should have increased
            debugging or not.  When True or False, this overrides the
            configuration file setting.
        """

    def _reset():
        """Reset the database to its pristine state.

        This is only used by the test framework.
        """

    # XXX Eventually we probably need to support a transaction manager
    # interface, e.g. begin(), commit(), abort().  We will probably also need
    # to support a shutdown() method for cleanly disconnecting from the
    # database.sy

    list_manager = Attribute(
        """The IListManager instance provided by the database layer.""")

    user_manager = Attribute(
        """The IUserManager instance provided by the database layer.""")

    message_store = Attribute(
        """The IMessageStore instance provided by the database layer.""")

    pendings = Attribute(
        """The IPending instance provided by the database layer.""")
