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
    'Prototype',
    ]


import os
import hashlib

from base64 import b32encode, urlsafe_b64encode
from cStringIO import StringIO
from email.utils import make_msgid
from string import Template
from urllib import quote
from urlparse import urljoin
from zope.interface import implements
from zope.interface.interface import adapter_hooks

from mailman.configuration import config
from mailman.interfaces.archiver import IArchiver, IPipermailMailingList
from mailman.interfaces.mailinglist import IMailingList
from mailman.queue import Switchboard

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
    """Adapt IMailingLists to IPipermailMailingList."""
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
            web_host = config.domains.get(mlist.host_name, mlist.host_name)
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



class Prototype:
    """A prototype of a third party archiver.

    Mailman proposes a draft specification for interoperability between list
    servers and archivers: <http://wiki.list.org/display/DEV/Stable+URLs>.
    """

    implements(IArchiver)

    name = 'prototype'
    is_enabled = False

    @staticmethod
    def list_url(mlist):
        """See `IArchiver`."""
        web_host = config.domains.get(mlist.host_name, mlist.host_name)
        return 'http://' + web_host

    @staticmethod
    def permalink(mlist, msg):
        """See `IArchiver`."""
        message_id = msg.get('message-id')
        # It is not the archiver's job to ensure the message has a Message-ID.
        assert message_id is not None, 'No Message-ID found'
        # The angle brackets are not part of the Message-ID.  See RFC 2822.
        if message_id.startswith('<') and message_id.endswith('>'):
            message_id = message_id[1:-1]
        digest = hashlib.sha1(message_id).digest()
        message_id_hash = b32encode(digest)
        del msg['x-message-id-hash']
        msg['X-Message-ID-Hash'] = message_id_hash
        return urljoin(Prototype.list_url(mlist), message_id_hash)

    @staticmethod
    def archive_message(mlist, message):
        """See `IArchiver`."""
        raise NotImplementedError



class MailArchive:
    """Public archiver at the Mail-Archive.com.

    Messages get archived at http://go.mail-archive.com.
    """

    implements(IArchiver)

    name = 'mail-archive'
    is_enabled = False

    @staticmethod
    def list_url(mlist):
        """See `IArchiver`."""
        if mlist.archive_private:
            return None
        return urljoin(config.MAIL_ARCHIVE_BASEURL,
                       quote(mlist.posting_address))

    @staticmethod
    def permalink(mlist, msg):
        """See `IArchiver`."""
        if mlist.archive_private:
            return None
        message_id = msg.get('message-id')
        # It is not the archiver's job to ensure the message has a Message-ID.
        assert message_id is not None, 'No Message-ID found'
        # The angle brackets are not part of the Message-ID.  See RFC 2822.
        start = (1 if message_id.startswith('<') else 0)
        end = (-1 if message_id.endswith('>') else None)
        message_id = message_id[start:end]
        sha = hashlib.sha1(message_id)
        sha.update(str(mlist.post_id))
        message_id_hash = urlsafe_b64encode(sha.digest())
        del msg['x-message-id-hash']
        msg['X-Message-ID-Hash'] = message_id_hash
        return urljoin(config.MAIL_ARCHIVE_BASEURL, message_id_hash)

    @staticmethod
    def archive_message(mlist, msg):
        """See `IArchiver`."""
        if mlist.archive_private:
            return
        outq = Switchboard(config.OUTQUEUE_DIR)
        outq.enqueue(
            msg,
            listname=mlist.fqdn_listname,
            recips=[config.MAIL_ARCHIVE_RECIPIENT])
