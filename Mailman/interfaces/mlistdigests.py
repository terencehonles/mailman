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

"""Interface for digest related information."""

from zope.interface import Interface, Attribute



class IMailingListDigests(Interface):
    """Digest related information for the mailing list."""

    volume_number = Attribute(
        """A monotonically increasing integer sequentially assigned to each
        new digest volume.  The volume number may be bumped either
        automatically (i.e. on a defined schedule) or manually.  When the
        volume number is bumped, the digest number is always reset to 1.""")

    digest_number = Attribute(
        """A sequence number for a specific digest in a given volume.  When
        the digest volume number is bumped, the digest number is reset to
        1.""")

    def bump():
        """Bump the digest's volume number to the next integer in the
        sequence, and reset the digest number to 1.
        """

    message_count = Attribute(
        """The number of messages in the digest currently being collected.""")

    digest_size = Attribute(
        """The approximate size in kilobytes of the digest currently being
        collected.""")

    messages = Attribute(
        """An iterator over all the messages in the digest currently being
        created.  Returns individual IPostedMessage objects.
        """)

    limits = Attribute(
        """An iterator over the IDigestLimiters associated with this digest.
        Each limiter can make a determination of whether the digest has
        reached the threshold for being automatically sent.""")

    def send():
        """Send this digest now."""

    decorators = Attribute(
        """An iterator over all the IDecorators associated with this digest.
        When a digest is being sent, each decorator may modify the final
        digest text.""")
