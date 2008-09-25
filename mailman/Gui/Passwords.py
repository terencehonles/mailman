# Copyright (C) 2001-2008 by the Free Software Foundation, Inc.
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

"""MailList mixin class managing the password pseudo-options."""

from Mailman.i18n import _
from Mailman.Gui.GUIBase import GUIBase



class Passwords(GUIBase):
    def GetConfigCategory(self):
        return 'passwords', _('Passwords')

    def handleForm(self, mlist, category, subcat, cgidata, doc):
        # Nothing more needs to be done
        pass
