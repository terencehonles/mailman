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

"""Cleanse certain headers from all messages."""


def process(mlist, msg):
    # Always remove this header from any outgoing messages, but be sure to do
    # this before the information on the header is actually used.
    del msg['approved']
    #
    # We remove other headers for anonymous lists
    if mlist.anonymous_list:
        del msg['reply-to']
        del msg['sender']
        msg['From'] = mlist.GetAdminEmail()
        msg['Reply-To'] = mlist.GetListEmail()
    #
    # Some headers can be used to fish for membership
    del msg['return-receipt-to']
    del msg['disposition-notification-to']
    del msg['x-confirm-reading-to']
