# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


"""Mixin class with list-digest handling methods and settings."""

import os
from stat import ST_SIZE

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman.Handlers import ToDigest
from Mailman.i18n import _



class Digester:
    def InitVars(self):
	# Configurable
	self.digestable = mm_cfg.DEFAULT_DIGESTABLE
	self.digest_is_default = mm_cfg.DEFAULT_DIGEST_IS_DEFAULT
	self.mime_is_default_digest = mm_cfg.DEFAULT_MIME_IS_DEFAULT_DIGEST
	self.digest_size_threshhold = mm_cfg.DEFAULT_DIGEST_SIZE_THRESHHOLD
	self.digest_send_periodic = mm_cfg.DEFAULT_DIGEST_SEND_PERIODIC
	self.next_post_number = 1
	self.digest_header = mm_cfg.DEFAULT_DIGEST_HEADER
	self.digest_footer = mm_cfg.DEFAULT_DIGEST_FOOTER
        self.digest_volume_frequency = mm_cfg.DEFAULT_DIGEST_VOLUME_FREQUENCY
	# Non-configurable.
	self.digest_members = {}
	self.next_digest_number = 1
        self.digest_last_sent_at = 0

    def GetConfigInfo(self):
        WIDTH = mm_cfg.TEXTFIELDWIDTH
        os.environ['LANG'] = self.preferred_language

	return [
            _("Batched-delivery digest characteristics."),

	    ('digestable', mm_cfg.Toggle, (_('No'), _('Yes')), 1,
	     _('Can list members choose to receive list traffic '
	       'bunched in digests?')),

	    ('digest_is_default', mm_cfg.Radio, 
	     (_('Regular'), _('Digest')), 0,
	     _('Which delivery mode is the default for new users?')),

	    ('mime_is_default_digest', mm_cfg.Radio, 
	     (_('Plain'), _('MIME')), 0,
	     _('When receiving digests, which format is default?')),

	    ('digest_size_threshhold', mm_cfg.Number, 3, 0,
	     _('How big in Kb should a digest be before it gets sent out?')),
            # Should offer a 'set to 0' for no size threshhold.

 	    ('digest_send_periodic', mm_cfg.Radio, (_('No'), _('Yes')), 1,
	     _('Should a digest be dispatched daily when the size threshold '
	       "isn't reached?")),

            ('digest_header', mm_cfg.Text, (4, WIDTH), 0,
	     _('Header added to every digest'),
             _("Text attached (as an initial message, before the table"
               " of contents) to the top of digests. ")
             + Utils.maketext('headfoot.html', raw=1, mlist=self)),

	    ('digest_footer', mm_cfg.Text, (4, WIDTH), 0,
	     _('Footer added to every digest'),
             _("Text attached (as a final message) to the bottom of digests. ")
             + Utils.maketext('headfoot.html', raw=1, mlist=self)),

            ('digest_volume_frequency', mm_cfg.Radio,
             (_('Yearly'), _('Monthly'), _('Quarterly'),
              _('Weekly'), _('Daily')), 0,
             _('How often should a new digest volume be started?'),
             _('''When a new digest volume is started, the volume number is
             incremented and the issue number is reset to 1.''')),

            ('_new_volume', mm_cfg.Toggle, (_('No'), _('Yes')), 0,
             _('Should Mailman start a new digest volume?'),
             _('''Setting this option instructs Mailman to start a new volume
             with the next digest sent out.''')),

            ('_send_digest_now', mm_cfg.Toggle, (_('No'), _('Yes')), 0,
             _('''Should Mailman send the next digest right now, if it is not
             empty?''')),
	    ]

    def SetUserDigest(self, sender, value, force=0):
	self.IsListInitialized()
	addr = self.FindUser(sender)
	if not addr:
	    raise Errors.MMNotAMemberError
        cpuser = self.GetUserSubscribedAddress(addr)
	if self.members.has_key(addr):
	    if value == 0:
		raise Errors.MMAlreadyUndigested
	    else:
		if not force and not self.digestable:
		    raise Errors.MMCantDigestError
		del self.members[addr]
		self.digest_members[addr] = cpuser
	else:
	    if value == 1:
		raise Errors.MMAlreadyDigested
	    else:
		if not force and not self.nondigestable:
		    raise Errors.MMMustDigestError
                try:
                    self.one_last_digest[addr] = self.digest_members[addr]
                except AttributeError:
                    self.one_last_digest = {addr: self.digest_members[addr]}
		del self.digest_members[addr]
		self.members[addr] = cpuser
        # BAW: This Save() can probably go away.
	self.Save()

    def send_digest_now(self):
        # Note: Handler.ToDigest.send_digests() handles bumping the digest
        # volume and issue number.
        digestmbox = os.path.join(self.fullpath(), 'digest.mbox')
        try:
            try:
                mboxfp = None
                # See if there's a digest pending for this mailing list
                if os.stat(digestmbox)[ST_SIZE] > 0:
                    mboxfp = open(digestmbox)
                    ToDigest.send_digests(self, mboxfp)
                    os.unlink(digestmbox)
            finally:
                if mboxfp:
                    mboxfp.close()
        except OSError, e:
            if e.errno <> errno.ENOENT: raise
            # List has no outstanding digests

    def bump_digest_volume(self):
        mlist.volume += 1
        mlist.next_digest_number = 1
