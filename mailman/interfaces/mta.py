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

"""Interface for mail transport agent integration."""

__metaclass__ = type
__all__ = [
    'IMailTransportAgent',
    ]


from zope.interface import Interface



class IMailTransportAgent(Interface):
    """Interface to the MTA."""

    def create(mlist):
        """Tell the MTA that the mailing list was created."""

    def delete(mlist):
        """Tell the MTA that the mailing list was deleted."""

    def regenerate():
        """Regenerate the full aliases file."""
