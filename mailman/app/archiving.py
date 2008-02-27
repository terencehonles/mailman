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

__all__ = [
    'Pipermail',
    'get_archiver',
    ]
__metaclass__ = type


from string import Template
from zope.interface import implements
from zope.interface.verify import verifyObject

from mailman.app.plugins import get_plugin
from mailman.configuration import config
from mailman.interfaces import IArchiver



class Pipermail:
    """The stock Pipermail archiver."""

    implements(IArchiver)

    def get_list_url(self, mlist):
        """See `IArchiver`."""
        if mlist.archive_private:
            url = mlist.script_url('private') + '/index.html'
        else:
            web_host = config.domains.get(mlist.host_name, mlist.host_name)
            url = Template(config.PUBLIC_ARCHIVE_URL).safe_substitute(
                listname=mlist.fqdn_listname,
                hostname=web_host,
                fqdn_listname=mlist.fqdn_listname,
                )
        return url

    def get_message_url(self, mlist, message):
        """See `IArchiver`."""
        # Not currently implemented.
        return None

    def archive_message(self, mlist, message):
        """See `IArchiver`."""
        return None



_archiver = None

def get_archiver():
    """Return the currently registered global archiver.

    Uses the plugin architecture to find the IArchiver instance.
    """
    global _archiver
    if _archiver is None:
        _archiver = get_plugin('mailman.archiver')()
        verifyObject(IArchiver, _archiver)
    return _archiver
