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

"""Base class for terminal chains."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Chain',
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



class TerminalChainBase:
    """A base chain that always matches and executes a method.

    The method is called 'process' and must be provided by the subclass.
    """
    implements(IChain, IChainIterator)

    def _process(self, mlist, msg, msgdata):
        """Process the message for the given mailing list.

        This must be overridden by subclasses.
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
        # Register the chain.
        config.chains[name] = self

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
