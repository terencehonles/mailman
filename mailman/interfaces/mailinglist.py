# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""Interface for a mailing list."""

__all__ = [
    'IMailingList',
    'Personalization',
    'ReplyToMunging',
    ]

from munepy import Enum
from zope.interface import Interface, Attribute



class Personalization(Enum):
    none = 0
    # Everyone gets a unique copy of the message, and there are a few more
    # substitution variables, but no headers are modified.
    individual = 1
    # All of the 'individual' personalization plus recipient header
    # modification.
    full = 2



class ReplyToMunging(Enum):
    # The Reply-To header is passed through untouched
    no_munging = 0
    # The mailing list's posting address is appended to the Reply-To header
    point_to_list = 1
    # An explicit Reply-To header is added
    explicit_header = 2



class IMailingList(Interface):
    """A mailing list."""

    list_name = Attribute(
        """The read-only short name of the mailing list.  Note that where a
        Mailman installation supports multiple domains, this short name may
        not be unique.  Use the fqdn_listname attribute for a guaranteed
        unique id for the mailing list.  This short name is always the local
        part of the posting email address.  For example, if messages are
        posted to mylist@example.com, then the list_name is 'mylist'.
        """)

    real_name = Attribute(
        """The short human-readable descriptive name for the mailing list.  By
        default, this is the capitalized `list_name`, but it can be changed to
        anything.  This is used in locations such as the message footers and
        Subject prefix.
        """)

    host_name = Attribute(
        """The read-only domain name 'hosting' this mailing list.  This is
        always the domain name part of the posting email address, and it may
        bear no relationship to the web url used to access this mailing list.
        For example, if messages are posted to mylist@example.com, then the
        host_name is 'example.com'.
        """)

    fqdn_listname = Attribute(
        """The read-only fully qualified name of the mailing list.  This is
        the guaranteed unique id for the mailing list, and it is always the
        address to which messages are posted, e.g. mylist@example.com.  It is
        always comprised of the list_name + '@' + host_name.
        """)

    posting_address = Attribute(
        """The address to which messages are posted for copying to the full
        list membership, where 'full' of course means those members for which
        delivery is currently enabled.
        """)

    no_reply_address = Attribute(
        """The address to which all messages will be immediately discarded,
        without prejudice or record.  This address is specific to the ddomain,
        even though it's available on the IMailingListAddresses interface.
        Generally, humans should never respond directly to this address.
        """)

    owner_address = Attribute(
        """The address which reaches the owners and moderators of the mailing
        list.  There is no address which reaches just the owners or just the
        moderators of a mailing list.
        """)

    request_address = Attribute(
        """The address which reaches the email robot for this mailing list.
        This robot can process various email commands such as changing
        delivery options, getting information or help about the mailing list,
        or processing subscrptions and unsubscriptions (although for the
        latter two, it's better to use the join_address and leave_address.
        """)

    bounces_address = Attribute(
        """The address which reaches the automated bounce processor for this
        mailing list.  Generally, humans should never respond directly to this
        address.
        """)

    join_address = Attribute(
        """The address to which subscription requests should be sent.  See
        subscribe_address for a backward compatible alias.
        """)

    leave_address = Attribute(
        """The address to which unsubscription requests should be sent.  See
        unsubscribe_address for a backward compatible alias.
        """)

    subscribe_address = Attribute(
        """Deprecated address to which subscription requests may be sent.
        This address is provided for backward compatibility only.  See
        join_address for the preferred alias.
        """)

    leave_address = Attribute(
        """Deprecated address to which unsubscription requests may be sent.
        This address is provided for backward compatibility only.  See
        leave_address for the preferred alias.
        """)

    def confirm_address(cookie=''):
        """The address used for various forms of email confirmation."""

    creation_date = Attribute(
        """The date and time that the mailing list was created.""")

    last_post_date = Attribute(
        """The date and time a message was last posted to the mailing list.""")

    post_id = Attribute(
        """A monotonically increasing integer sequentially assigned to each
        list posting.""")

    last_digest_date = Attribute(
        """The date and time a digest of this mailing list was last sent.""")

    owners = Attribute(
        """The IUser owners of this mailing list.

        This does not include the IUsers who are moderators but not owners of
        the mailing list.""")

    moderators = Attribute(
        """The IUser moderators of this mailing list.

        This does not include the IUsers who are owners but not moderators of
        the mailing list.""")

    administrators = Attribute(
        """The IUser administrators of this mailing list.

        This includes the IUsers who are both owners and moderators of the
        mailing list.""")

    members = Attribute(
        """An iterator over all the members of the mailing list, regardless of
        whether they are to receive regular messages or digests, or whether
        they have their delivery disabled or not.""")

    regular_members = Attribute(
        """An iterator over all the IMembers who are to receive regular
        postings (i.e. non-digests) from the mailing list, regardless of
        whether they have their delivery disabled or not.""")

    digest_members = Attribute(
        """An iterator over all the IMembers who are to receive digests of
        postings to this mailing list, regardless of whether they have their
        deliver disabled or not, or of the type of digest they are to
        receive.""")

    subscribers = Attribute(
        """An iterator over all IMembers subscribed to this list, with any
        role.
        """)

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

    protocol = Attribute(
        """The protocol scheme used to contact this list's server.

        The web server on thi protocol provides the web interface for this
        mailing list.  The protocol scheme should be 'http' or 'https'.""")

    web_host = Attribute(
        """This list's web server's domain.

        The read-only domain name of the host to contact for interacting with
        the web interface of the mailing list.""")

    def script_url(target, context=None):
        """Return the url to the given script target.

        If 'context' is not given, or is None, then an absolute url is
        returned.  If context is given, it must be an IMailingListRequest
        object, and the returned url will be relative to that object's
        'location' attribute.
        """

    pipeline = Attribute(
        """The name of this mailing list's processing pipeline.

        Every mailing list has a processing pipeline that messages flow
        through once they've been accepted.
        """)

    data_path = Attribute(
        """The file system path to list-specific data.

        An example of list-specific data is the temporary digest mbox file
        that gets created to accumlate messages for the digest.
        """)
