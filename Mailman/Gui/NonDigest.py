# Copyright (C) 2001 by the Free Software Foundation, Inc.
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

"""MailList mixin class managing the non-digest delivery options.
"""

from Mailman import mm_cfg
from Mailman import Utils
from Mailman.i18n import _



class NonDigest:
    def GetConfigCategory(self):
        return 'nondigest', _('Non-digest delivery options')

    def GetConfigInfo(self, mlist):
        WIDTH = mm_cfg.TEXTFIELDWIDTH

        return [
            _("Policies concerning immediately delivered list traffic."),

            ('nondigestable', mm_cfg.Toggle, (_('No'), _('Yes')), 1,
             _("""Can subscribers choose to receive mail immediately, rather
             than in batched digests?""")),

            ('msg_header', mm_cfg.Text, (4, WIDTH), 0,
             _('Header added to mail sent to regular list members'),
             _('''Text prepended to the top of every immediately-delivery
             message. ''') + Utils.maketext('headfoot.html',
                                            mlist=mlist, raw=1)),
            
            ('msg_footer', mm_cfg.Text, (4, WIDTH), 0,
             _('Footer added to mail sent to regular list members'),
             _('''Text appended to the bottom of every immediately-delivery
             message. ''') + Utils.maketext('headfoot.html',
                                            mlist=mlist, raw=1)),
            ]

