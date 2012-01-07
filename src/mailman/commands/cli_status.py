# Copyright (C) 2010-2012 by the Free Software Foundation, Inc.
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
    'Status',
    ]


import socket

from zope.interface import implements

from mailman.bin.master import WatcherState, master_state
from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand



class Status:
    """Status of the Mailman system."""

    implements(ICLISubCommand)

    name = 'status'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        pass

    def process(self, args):
        """See `ICLISubCommand`."""
        status, lock = master_state()
        if status is WatcherState.none:
            message = _('GNU Mailman is not running')
        elif status is WatcherState.conflict:
            hostname, pid, tempfile = lock.details
            message = _('GNU Mailman is running (master pid: $pid)')
        elif status is WatcherState.stale_lock:
            hostname, pid, tempfile = lock.details
            message =_('GNU Mailman is stopped (stale pid: $pid)')
        else:
            hostname, pid, tempfile = lock.details
            fqdn_name = socket.getfqdn()
            assert status is WatcherState.host_mismatch, (
                'Invalid enum value: %s' % status)
            message = _('GNU Mailman is in an unexpected state '
                        '($hostname != $fqdn_name)')
        print message
        return int(status)
