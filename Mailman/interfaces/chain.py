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

"""Interface describing the basics of chains and links."""

from munepy import Enum
from zope.interface import Interface, Attribute



class IChain(Interface):
    """A chain of rules."""

    name = Attribute('Chain name; must be unique.')
    description = Attribute('A brief description of the chain.')

    def process(mlist, msg, msgdata):
        """Process the message through the chain.

        Processing a message involves running through each link in the chain,
        until a jump to another chain occurs or the chain reaches the end.
        Reaching the end of the chain with no other disposition is equivalent
        to discarding the message.

        :param mlist: The mailing list object.
        :param msg: The message object.
        :param msgdata: The message metadata.
        """



class IMutableChain(IChain):
    """Like `IChain` but can be mutated."""

    def append_link(link):
        """Add a new chain link to the end of this chain.

        :param link: The chain link to add.
        """

    def flush():
        """Delete all links in this chain."""



class IChainLink(Interface):
    """A link in the chain."""

    rule = Attribute('The rule to run for this link.')

    jump = Attribute(
        """The jump action to perform when the rule matches.  This may be None
        to simply process the next link in the chain.
        """)
