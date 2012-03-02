# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""Module stuff."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Confirm',
    ]


from zope.component import getUtility
from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.command import ContinueProcessing, IEmailCommand
from mailman.interfaces.registrar import IRegistrar



class Confirm:
    """The email 'confirm' command."""

    implements(IEmailCommand)

    name = 'confirm'
    argument_description = 'token'
    description = _('Confirm a subscription request.')
    short_description = description

    def process(self, mlist, msg, msgdata, arguments, results):
        """See `IEmailCommand`."""
        # The token must be in the arguments.
        if len(arguments) == 0:
            print >> results, _('No confirmation token found')
            return ContinueProcessing.no
        # Make sure we don't try to confirm the same token more than once.
        token = arguments[0]
        tokens = getattr(results, 'confirms', set())
        if token in tokens:
            # Do not try to confirm this one again.
            return ContinueProcessing.yes
        tokens.add(token)
        results.confirms = tokens
        succeeded = getUtility(IRegistrar).confirm(token)
        if succeeded:
            print >> results, _('Confirmed')
            return ContinueProcessing.yes
        print >> results, _('Confirmation token did not match')
        return ContinueProcessing.no
