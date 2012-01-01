# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""Interface for switchboards."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ISwitchboard',
    ]


from zope.interface import Interface, Attribute



class ISwitchboard(Interface):
    """The switchboard."""

    name = Attribute(
        """The name of the switchboard's queue.""")

    queue_directory = Attribute(
        """The queue directory this switchboard is responsible for.

        This should be a subdirectory of the system-wide top-level queue
        directory.
        """)

    def enqueue(_msg, _metadata=None, **_kws):
        """Store the message and metadata in the switchboard's queue.

        When metadata is not given, an empty metadata dictionary is used.  The
        keyword arguments are added to the metadata dictonary, with precedence
        given to the keyword arguments.

        The base name of the message file is returned.
        """

    def dequeue(filebase):
        """Return the message and metadata contained in the named file.

        filebase is the base name of the message file as returned by the
        .enqueue() method.  This file must exist and contain a message and
        metadata.  The message file is preserved in a backup file, which must
        be removed by calling the .finish() method.

        Returned is a 2-tuple of the form (message, metadata).
        """

    def finish(filebase, preserve=False):
        """Remove the backup file for filebase.

        If preserve is True, then the backup file is actually just renamed to
        a preservation file instead of being unlinked.
        """

    files = Attribute(
        """An iterator over all the .pck files in the queue directory.

        The base names of the matching files are returned.
        """)

    def get_files(extension='.pck'):
        """Like the 'files' attribute, but accepts an alternative extension.

        Only the files in the queue directory that have a matching extension
        are returned.  Like 'files', the base names of the matching files are
        returned.
        """

    def recover_backup_files():
        """Move all backup files to active message files.

        It is impossible for both the .bak and .pck files to exist at the same
        time, so moving them is enough to ensure that a normal dequeing
        operation will handle them.
        """
