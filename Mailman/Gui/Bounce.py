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

from Mailman import mm_cfg
from Mailman.i18n import _



class Bounce:
    def GetConfigCategory(self):
        return 'bounce', _('Bounce detection')

    def GetConfigInfo(self, mlist):
        return [
            _('''Policies regarding systematic processing of bounce messages,
            to help automate recognition and handling of defunct
            addresses.'''),
            
            ('bounce_processing', mm_cfg.Toggle, (_('No'), _('Yes')), 0,
             _('Try to figure out error messages automatically?')),

            ('minimum_removal_date', mm_cfg.Number, 3, 0,
             _('''Minimum number of days an address has been non-fatally bad
             before we take action''')),

            ('minimum_post_count_before_bounce_action', mm_cfg.Number, 3, 0,
             _('''Minimum number of posts to the list since members first
             bounce before we consider removing them from the list''')),

            ('max_posts_between_bounces', mm_cfg.Number, 3, 0,
             _('''Maximum number of messages your list gets in an hour. (Yes,
             bounce detection finds this info useful)''')),

            ('automatic_bounce_action', mm_cfg.Radio,
             (_("Do nothing"),
              _("Disable and notify me"),
              _("Disable and DON'T notify me"),
              _("Remove and notify me")),
             0,
             _("Action when critical or excessive bounces are detected."))
            ]
