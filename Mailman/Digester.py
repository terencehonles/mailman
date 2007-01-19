# Copyright (C) 1998-2007 by the Free Software Foundation, Inc.
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


"""Mixin class with list-digest handling methods and settings."""

import os
import errno

from Mailman import Errors
from Mailman import Utils
from Mailman.Handlers import ToDigest
from Mailman.configuration import config
from Mailman.i18n import _



class Digester:
    def InitVars(self):
        # Configurable
        self.digestable = config.DEFAULT_DIGESTABLE
        self.digest_is_default = config.DEFAULT_DIGEST_IS_DEFAULT
        self.mime_is_default_digest = config.DEFAULT_MIME_IS_DEFAULT_DIGEST
        self.digest_size_threshhold = config.DEFAULT_DIGEST_SIZE_THRESHHOLD
        self.digest_send_periodic = config.DEFAULT_DIGEST_SEND_PERIODIC
        self.next_post_number = 1
        self.digest_header = config.DEFAULT_DIGEST_HEADER
        self.digest_footer = config.DEFAULT_DIGEST_FOOTER
        self.digest_volume_frequency = config.DEFAULT_DIGEST_VOLUME_FREQUENCY
        # Non-configurable.
        self.one_last_digest = {}
        self.digest_members = {}
        self.next_digest_number = 1
        self.digest_last_sent_at = 0

    def send_digest_now(self):
        # Note: Handler.ToDigest.send_digests() handles bumping the digest
        # volume and issue number.
        digestmbox = os.path.join(self.fullpath(), 'digest.mbox')
        try:
            try:
                mboxfp = None
                # See if there's a digest pending for this mailing list
                if os.stat(digestmbox).st_size > 0:
                    mboxfp = open(digestmbox)
                    ToDigest.send_digests(self, mboxfp)
                    os.unlink(digestmbox)
            finally:
                if mboxfp:
                    mboxfp.close()
        except OSError, e:
            if e.errno <> errno.ENOENT:
                raise
            # List has no outstanding digests
            return False
        return True

    def bump_digest_volume(self):
        self.volume += 1
        self.next_digest_number = 1
