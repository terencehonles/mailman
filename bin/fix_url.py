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

"""Reset a list's web_page_url attribute to the default setting.

This script is intended to be run as a bin/withlist script, i.e.

% bin/withlist -l -r fix_url <mylist>
"""

from Mailman import mm_cfg
from Mailman.i18n import _



def fix_url(mlist):
    mlist.web_page_url = mm_cfg.DEFAULT_URL_PATTERN % mm_cfg.DEFAULT_URL_HOST
    print _('Saving list')
    mlist.Save()
