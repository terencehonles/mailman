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

"""Application level archiving support."""

__metaclass__ = type
__all__ = [
    'Pipermail',
    'get_primary_archiver',
    ]


import os
import pkg_resources

from string import Template
from zope.interface import implements
from zope.interface.verify import verifyObject

from mailman.app.plugins import get_plugins
from mailman.configuration import config
from mailman.interfaces import IArchiver

from mailman.Archiver.HyperArch import HyperArchive
from cStringIO import StringIO



class PipermailMailingListAdapter:
    """An adapter for MailingList objects to work with Pipermail."""

    def __init__(self, mlist):
        self._mlist = mlist

    def __getattr__(self, name):
        return getattr(self._mlist, name)

    def archive_dir(self):
        """The directory for storing Pipermail artifacts."""
        if self._mlist.archive_private:
            basedir = config.PRIVATE_ARCHIVE_FILE_DIR
        else:
            basedir = config.PUBLIC_ARCHIVE_FILE_DIR
        return os.path.join(basedir, self._mlist.fqdn_listname)



class Pipermail:
    """The stock Pipermail archiver."""

    implements(IArchiver)

    def __init__(self, mlist):
        self._mlist = mlist

    def get_list_url(self):
        """See `IArchiver`."""
        if self._mlist.archive_private:
            url = self._mlist.script_url('private') + '/index.html'
        else:
            web_host = config.domains.get(
                self._mlist.host_name, self._mlist.host_name)
            url = Template(config.PUBLIC_ARCHIVE_URL).safe_substitute(
                listname=self._mlist.fqdn_listname,
                hostname=web_host,
                fqdn_listname=self._mlist.fqdn_listname,
                )
        return url

    def get_message_url(self, message):
        """See `IArchiver`."""
        # Not currently implemented.
        return None

    def archive_message(self, message):
        """See `IArchiver`."""
        text = str(message)
        fileobj = StringIO(text)
        h = HyperArchive(PipermailMailingListAdapter(self._mlist))
        h.processUnixMailbox(fileobj)
        h.close()
        fileobj.close()
        # There's no good way to know the url for the archived message.
        return None



def get_primary_archiver(mlist):
    """Return the primary archiver."""
    entry_points = list(pkg_resources.iter_entry_points('mailman.archiver'))
    if len(entry_points) == 0:
        return None
    for ep in entry_points:
        if ep.name == 'default':
            return ep.load()(mlist)
    return None
