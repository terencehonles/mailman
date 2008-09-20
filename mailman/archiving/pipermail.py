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

"""Pipermail archiver."""

__metaclass__ = type
__all__ = [
    'Pipermail',
    ]


import os

from cStringIO import StringIO
from string import Template
from zope.interface import implements
from zope.interface.interface import adapter_hooks

from mailman.configuration import config
from mailman.interfaces.archiver import IArchiver, IPipermailMailingList
from mailman.interfaces.mailinglist import IMailingList

from mailman.Archiver.HyperArch import HyperArchive



class PipermailMailingListAdapter:
    """An adapter for MailingList objects to work with Pipermail."""

    implements(IPipermailMailingList)

    def __init__(self, mlist):
        self._mlist = mlist

    def __getattr__(self, name):
        return getattr(self._mlist, name)

    def archive_dir(self):
        """See `IPipermailMailingList`."""
        if self._mlist.archive_private:
            basedir = config.PRIVATE_ARCHIVE_FILE_DIR
        else:
            basedir = config.PUBLIC_ARCHIVE_FILE_DIR
        return os.path.join(basedir, self._mlist.fqdn_listname)


def adapt_mailing_list_for_pipermail(iface, obj):
    """Adapt `IMailingLists` to `IPipermailMailingList`.

    :param iface: The interface to adapt to.
    :type iface: `zope.interface.Interface`
    :param obj: The object being adapted.
    :type obj: any object
    :return: An `IPipermailMailingList` instance if adaptation succeeded or
        None if it didn't.
    """
    if IMailingList.providedBy(obj) and iface is IPipermailMailingList:
        return PipermailMailingListAdapter(obj)
    return None

adapter_hooks.append(adapt_mailing_list_for_pipermail)



class Pipermail:
    """The stock Pipermail archiver."""

    implements(IArchiver)

    name = 'pipermail'
    is_enabled = False

    @staticmethod
    def list_url(mlist):
        """See `IArchiver`."""
        if mlist.archive_private:
            url = mlist.script_url('private') + '/index.html'
        else:
            web_host = config.domains[mlist.host_name].url_host
            url = Template(config.PUBLIC_ARCHIVE_URL).safe_substitute(
                listname=mlist.fqdn_listname,
                hostname=web_host,
                fqdn_listname=mlist.fqdn_listname,
                )
        return url

    @staticmethod
    def permalink(mlist, message):
        """See `IArchiver`."""
        # Not currently implemented.
        return None

    @staticmethod
    def archive_message(mlist, message):
        """See `IArchiver`."""
        text = str(message)
        fileobj = StringIO(text)
        h = HyperArchive(IPipermailMailingList(mlist))
        h.processUnixMailbox(fileobj)
        h.close()
        fileobj.close()
        # There's no good way to know the url for the archived message.
        return None
