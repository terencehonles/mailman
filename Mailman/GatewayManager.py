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

"""Mixin class for configuring Usenet gateway.

All the actual functionality is in Handlers/ToUsenet.py for the mail->news
gateway and cron/gate_news for the news->mail gateway.

"""

from Mailman import mm_cfg
from Mailman.i18n import _


class GatewayManager:
    def InitVars(self):
        # Configurable
        self.nntp_host = mm_cfg.DEFAULT_NNTP_HOST
        self.linked_newsgroup = ''
        self.gateway_to_news = 0
        self.gateway_to_mail = 0

    def GetConfigInfo(self):
        WIDTH = mm_cfg.TEXTFIELDWIDTH

        return [
            _('Mail-to-News and News-to-Mail gateway services.'),

            ('nntp_host', mm_cfg.String, WIDTH, 0,
             _('''The Internet address of the machine your News server is
             running on.'''),
             _('''The News server is not part of Mailman proper.  You have to
             already have access to a NNTP server, and that NNTP server has to
             recognize the machine this mailing list runs on as a machine
             capable of reading and posting news.''')),

            ('linked_newsgroup', mm_cfg.String, WIDTH, 0,
              _('The name of the Usenet group to gateway to and/or from.')),

            ('gateway_to_news',  mm_cfg.Toggle, (_('No'), _('Yes')), 0,
             _('''Should new posts to the mailing list be sent to the
             newsgroup?''')),

            ('gateway_to_mail',  mm_cfg.Toggle, (_('No'), _('Yes')), 0,
             _('''Should new posts to the newsgroup be sent to the mailing
             list?''')),

            ('_mass_catchup', mm_cfg.Toggle, (_('No'), _('Yes')), 0,
             _('Should Mailman perform a <em>catchup</em> on the newsgroup?'),
             _('''When you tell Mailman to perform a catchup on the newsgroup,
             this means that you want to start gating messages to the mailing
             list with the next new message found.  All earlier messages on
             the newsgroup will be ignored.  This is as if you were reading
             the newsgroup yourself, and you marked all current messages as
             <em>read</em>.  By catching up, your mailing list members will
             not see any of the earlier messages.'''))
            ]
