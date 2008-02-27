# Copyright (C) 2001-2008 by the Free Software Foundation, Inc.
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

from mailman.configuration import config
from mailman.queue import Switchboard



def inject(listname, msg, recips=None, qdir=None):
    if qdir is None:
        qdir = config.INQUEUE_DIR
    queue = Switchboard(qdir)
    kws = dict(
        listname=listname,
        tolist=True,
        _plaintext=True,
        )
    if recips is not None:
        kws['recips'] = recips
    queue.enqueue(msg, **kws)
