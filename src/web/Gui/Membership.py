# Copyright (C) 2001-2009 by the Free Software Foundation, Inc.
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

"""MailList mixin class managing the membership pseudo-options."""

from Mailman.i18n import _



class Membership:
    def GetConfigCategory(self):
        return 'members', _('Membership&nbsp;Management...')

    def GetConfigSubCategories(self, category):
        if category == 'members':
            return [('list',   _('Membership&nbsp;List')),
                    ('add',    _('Mass&nbsp;Subscription')),
                    ('remove', _('Mass&nbsp;Removal')),
                    ]
        return None
