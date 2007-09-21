# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

"""Application level archiving support."""

from string import Template

from Mailman.configuration import config



def get_base_archive_url(mlist):
    if mlist.archive_private:
        url = mlist.script_url('private') + '/index.html'
    else:
        web_host = config.domains.get(mlist.host_name, mlist.host_name)
        url = Template(config.PUBLIC_ARCHIVE_URL).safe_substitute(
            listname=mlist.fqdn_listname,
            hostname=web_host,
            fqdn_listname=mlist.fqdn_listname,
            )
    return url
