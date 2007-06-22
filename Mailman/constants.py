# Copyright (C) 2006-2007 by the Free Software Foundation, Inc.
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

"""Various constants and enumerations."""

from munepy import Enum
from zope.interface import implements

from Mailman.interfaces import IPreferences



class DeliveryMode(Enum):
    # Regular (i.e. non-digest) delivery
    regular = 1
    # Plain text digest delivery
    plaintext_digests = 2
    # MIME digest delivery
    mime_digests = 3
    # Summary digests
    summary_digests = 4



class DeliveryStatus(Enum):
    # Delivery is enabled
    enabled = 1
    # Delivery was disabled by the user
    by_user = 2
    # Delivery was disabled due to bouncing addresses
    by_bounces = 3
    # Delivery was disabled by an administrator or moderator
    by_moderator = 4



class MemberRole(Enum):
    member = 1
    owner = 2
    moderator = 3



class SystemDefaultPreferences(object):
    implements(IPreferences)

    acknowledge_posts = False
    hide_address = True
    preferred_language = 'en'
    receive_list_copy = True
    receive_own_postings = True
    delivery_mode = DeliveryMode.regular
    delivery_status = DeliveryStatus.enabled



class ReplyToMunging(Enum):
    # The Reply-To header is passed through untouched
    no_munging = 0
    # The mailing list's posting address is appended to the Reply-To header
    point_to_list = 1
    # An explicit Reply-To header is added
    explicit_header = 2
