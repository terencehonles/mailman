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

"""Base class for terminal chains."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Chain',
    'ChainNotification',
    'Link',
    'TerminalChainBase',
    ]


from zope.interface import implements

from mailman.config import config
from mailman.interfaces.chain import (
    IChain, IChainIterator, IChainLink, IMutableChain, LinkAction)



class Link:
    """A chain link."""
    implements(IChainLink)

    def __init__(self, rule, action=None, chain=None, function=None):
        self.rule = rule
        self.action = (LinkAction.defer if action is None else action)
        self.chain = chain
        self.function = function

    def __repr__(self):
        message = '<Link "if {0.rule.name} then {0.action} '
        if self.chain is None and self.function is not None:
            message += '{0.function}()'
        elif self.chain is not None and self.function is None:
            message += '{0.chain.name}'
        elif self.chain is None and self.function is None:
            pass
        else:
            message += '{0.chain.name} {0.function}()'
        message += '">'
        return message.format(self)



class TerminalChainBase:
    """A base chain that always matches and executes a method.

    The method is called '_process()' and must be provided by the subclass.
    """
    implements(IChain, IChainIterator)

    def _process(self, mlist, msg, msgdata):
        """Process the message for the given mailing list.

        This must be overridden by subclasses.

        :param mlist: The mailing list.
        :param msg: The message.
        :param msgdata: The message metadata.
        """
        raise NotImplementedError

    def get_links(self, mlist, msg, msgdata):
        """See `IChain`."""
        return iter(self)

    def __iter__(self):
        """See `IChainIterator`."""
        truth = config.rules['truth']
        # First, yield a link that always runs the process method.
        yield Link(truth, LinkAction.run, function=self._process)
        # Now yield a rule that stops all processing.
        yield Link(truth, LinkAction.stop)



class Chain:
    """Generic chain base class."""
    implements(IMutableChain)

    def __init__(self, name, description):
        assert name not in config.chains, (
            'Duplicate chain name: {0}'.format(name))
        self.name = name
        self.description = description
        self._links = []

    def append_link(self, link):
        """See `IMutableChain`."""
        self._links.append(link)

    def flush(self):
        """See `IMutableChain`."""
        self._links = []

    def get_links(self, mlist, msg, msgdata):
        """See `IChain`."""
        return iter(ChainIterator(self))

    def get_iterator(self):
        """Return an iterator over the links."""
        # We do it this way in order to preserve a separation of interfaces,
        # and allows .get_links() to be overridden.
        for link in self._links:
            yield link



class ChainIterator:
    """Generic chain iterator."""

    implements(IChainIterator)

    def __init__(self, chain):
        self._chain = chain

    def __iter__(self):
        """See `IChainIterator`."""
        return self._chain.get_iterator()



class ChainNotification:
    """Base class for chain notification events."""

    def __init__(self, mlist, msg, msgdata, chain):
        self.mlist = mlist
        self.msg = msg
        self.msgdata = msgdata
        self.chain = chain
