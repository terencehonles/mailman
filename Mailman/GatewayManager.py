# Copyright (C) 1998 by the Free Software Foundation, Inc.
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



class GatewayManager:
    def InitVars(self):
        # Configurable
        self.nntp_host        = ''
        self.linked_newsgroup = ''
        self.gateway_to_news  = 0
        self.gateway_to_mail  = 0

    def GetConfigInfo(self):
        WIDTH = mm_cfg.TEXTFIELDWIDTH

        return [
            'Mail-to-News and News-to-Mail gateway services.',
            ('nntp_host', mm_cfg.String, WIDTH, 0,
             'The Internet address of the machine your News server '
             'is running on.',
             'The News server is not part of Mailman proper.  You have to '
             'already have access to a NNTP server, and that NNTP server '
             'has to recognize the machine this mailing list runs on as '
             'a machine capable of reading and posting news.'),

            ('linked_newsgroup', mm_cfg.String, WIDTH, 0,
              'The name of the Usenet group to gateway to and/or from.'),

            ('gateway_to_news',  mm_cfg.Toggle, ('No', 'Yes'), 0,
             'Should posts to the mailing list be resent to the '
             'newsgroup?'),

            ('gateway_to_mail',  mm_cfg.Toggle, ('No', 'Yes'), 0,
             'Should newsgroup posts not sent from the list be resent '
             'to the list?')
            ]
