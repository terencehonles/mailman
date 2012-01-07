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
    'Mailbox',
    ]


# Use a single file format for the digest mailbox because this makes it easier
# to calculate the current size of the mailbox.  This way, we don't have to
# carry around or store the size of the mailbox, we can just stat the file to
# get its size.  MMDF is slightly more sane than mbox; it's primary advantage
# for us is that it does no 'From' mangling.
# mangling.
from mailbox import MMDF



class Mailbox(MMDF):
    """A mailbox that interoperates with the 'with' statement."""

    def __enter__(self):
        self.lock()
        return self

    def __exit__(self, *exc):
        self.flush()
        self.unlock()
        # Don't suppress the exception.
        return False
