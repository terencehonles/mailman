# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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
from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors



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
	# Non-configurable.
	self.digest_members = {}
	self.next_digest_number = 1

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
             + Utils.maketext('headfoot.html', lang=self.preferred_language,
                              raw=1)),

	    ('digest_footer', mm_cfg.Text, (4, WIDTH), 0,
	     _('Footer added to every digest'),
             _("Text attached (as a final message) to the bottom of digests. ")
             + Utils.maketext('headfoot.html', lang=self.preferred_language,
                              raw=1)),
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
	self.Save()
