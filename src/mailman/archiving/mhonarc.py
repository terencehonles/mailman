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

"""MHonArc archiver."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'MHonArc',
    ]


import logging
import subprocess

from urlparse import urljoin
from zope.interface import implements

from mailman.config import config
from mailman.interfaces.archiver import IArchiver
from mailman.utilities.string import expand


log = logging.getLogger('mailman.archiver')



class MHonArc:
    """Local MHonArc archiver."""

    implements(IArchiver)

    name = 'mhonarc'

    @staticmethod
    def list_url(mlist):
        """See `IArchiver`."""
        # XXX What about private MHonArc archives?
        return expand(config.archiver.mhonarc.base_url,
                      dict(listname=mlist.fqdn_listname,
                           hostname=mlist.domain.url_host,
                           fqdn_listname=mlist.fqdn_listname,
                           ))

    @staticmethod
    def permalink(mlist, msg):
        """See `IArchiver`."""
        # XXX What about private MHonArc archives?
        # It is the LMTP server's responsibility to ensure that the message
        # has a X-Message-ID-Hash header.  If it doesn't then there's no
        # permalink.
        message_id_hash = msg.get('x-message-id-hash')
        if message_id_hash is None:
            return None
        return urljoin(MHonArc.list_url(mlist), message_id_hash)

    @staticmethod
    def archive_message(mlist, msg):
        """See `IArchiver`."""
        substitutions = config.__dict__.copy()
        substitutions['listname'] = mlist.fqdn_listname
        command = expand(config.archiver.mhonarc.command, substitutions)
        proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=True)
        stdout, stderr = proc.communicate(msg.as_string())
        if proc.returncode != 0:
            log.error('%s: mhonarc subprocess had non-zero exit code: %s' %
                      (msg['message-id'], proc.returncode))
        log.info(stdout)
        log.error(stderr)
