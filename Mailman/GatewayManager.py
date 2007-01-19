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

"""Mixin class for configuring Usenet gateway.

All the actual functionality is in Handlers/ToUsenet.py for the mail->news
gateway and cron/gate_news for the news->mail gateway.

"""

from Mailman.configuration import config



class GatewayManager:
    def InitVars(self):
        # Configurable
        self.nntp_host = config.DEFAULT_NNTP_HOST
        self.linked_newsgroup = ''
        self.gateway_to_news = False
        self.gateway_to_mail = False
        self.news_prefix_subject_too = True
        # In patch #401270, this was called newsgroup_is_moderated, but the
        # semantics weren't quite the same.
        self.news_moderation = False
