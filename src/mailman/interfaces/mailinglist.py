# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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

"""Interface for a mailing list."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'DigestFrequency',
    'IAcceptableAlias',
    'IAcceptableAliasSet',
    'IMailingList',
    'Personalization',
    'ReplyToMunging',
    ]


from lazr.restful.declarations import (
    export_as_webservice_entry, exported)
from munepy import Enum
from zope.interface import Interface, Attribute
from zope.schema import TextLine

from mailman.core.i18n import _



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


class DigestFrequency(Enum):
    yearly = 0
    monthly = 1
    quarterly = 2
    weekly = 3
    daily = 4



class IMailingList(Interface):
    """A mailing list."""

    # Use a different singular and plural name for the resource type than
    # lazr.restful gives it as a default (which is normally taken from the
    # interface name).
    export_as_webservice_entry('list', 'lists')

    # List identity

    list_name = exported(TextLine(
        title=_('Short name'),
        description=_("""\
        The read-only short name of the mailing list.  Note that where a
        Mailman installation supports multiple domains, this short name may
        not be unique.  Use the fqdn_listname attribute for a guaranteed
        unique id for the mailing list.  This short name is always the local
        part of the posting email address.  For example, if messages are
        posted to mylist@example.com, then the list_name is 'mylist'.
        """)))

    host_name = exported(TextLine(
        title=_('Host name'),
        description=_("""\
        The read-only domain name 'hosting' this mailing list.  This is always
        the domain name part of the posting email address, and it may bear no
        relationship to the web url used to access this mailing list.  For
        example, if messages are posted to mylist@example.com, then the
        host_name is 'example.com'.
        """)))

    fqdn_listname = exported(TextLine(
        title=_('Fully qualified list name'),
        description=_("""\
        The read-only fully qualified name of the mailing list.  This is the
        guaranteed unique id for the mailing list, and it is always the
        address to which messages are posted, e.g. mylist@example.com.  It is
        always comprised of the list_name + '@' + host_name.
        """)))

    real_name = exported(TextLine(
        title=_('Real name'),
        description=_("""\
        The short human-readable descriptive name for the mailing list.  By
        default, this is the capitalized `list_name`, but it can be changed to
        anything.  This is used in locations such as the message footers and
        Subject prefix.
        """)))

    list_id = Attribute(
        """The RFC 2919 List-ID header value.""")

    include_list_post_header = Attribute(
        """Flag specifying whether to include the RFC 2369 List-Post header.
        This is usually set to True, except for announce-only lists.""")

    include_rfc2369_headers = Attribute(
        """Flag specifying whether to include any RFC 2369 header, including
        the RFC 2919 List-ID header.""")

    # Contact addresses

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

    digest_last_sent_at = Attribute(
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

    volume = Attribute(
        """A monotonically increasing integer sequentially assigned to each
        new digest volume.  The volume number may be bumped either
        automatically (i.e. on a defined schedule) or manually.  When the
        volume number is bumped, the digest number is always reset to 1.""")

    next_digest_number = Attribute(
        """A sequence number for a specific digest in a given volume.  When
        the digest volume number is bumped, the digest number is reset to
        1.""")

    digest_size_threshold = Attribute(
        """The maximum (approximate) size in kilobytes of the digest currently
        being collected.""")

    def send_one_last_digest_to(address, delivery_mode):
        """Make sure to send one last digest to an address.

        This is used when a person transitions from digest delivery to regular
        delivery and wants to make sure they don't miss anything.  By
        indicating that they'd like to receive one last digest, they will
        ensure continuity in receiving mailing lists posts.

        :param address: The address of the person receiving one last digest.
        :type address: `IAddress`
        :param delivery_mode: The type of digest to receive.
        :type delivery_mode: `DeliveryMode`
        """

    last_digest_recipients = Attribute(
        """An iterator over the addresses that should receive one last digest.

        Items are 2-tuples of (`IAddress`, `DeliveryMode`).  The one last
        digest recipients are cleared.
        """)

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

    filter_content = Attribute(
        """Flag specifying whether to filter a message's content.

        Filtering is performed on MIME type and file name extension.
        """)

    convert_html_to_plaintext = Attribute(
        """Flag specifying whether text/html parts should be converted.

        When True, after filtering, if there are any text/html parts left in
        the original message, they are converted to text/plain.
        """)

    collapse_alternatives = Attribute(
        """Flag specifying whether multipart/alternatives should be collapsed.

        After all MIME content filtering is complete, collapsing alternatives
        replaces the outer multipart/alternative parts with the first
        subpart.
        """)

    filter_types = Attribute(
        """Sequence of MIME types that should be filtered out.

        These can be either main types or main/sub types.  Set this attribute
        to a sequence to change it, or to None to empty it.
        """)

    pass_types = Attribute(
        """Sequence of MIME types to explicitly pass.

        These can be either main types or main/sub types.  Set this attribute
        to a sequence to change it, or to None to empty it.  Pass types are
        consulted after filter types, and only if `pass_types` is non-empty.
        """)
        
    filter_extensions = Attribute(
        """Sequence of file extensions that should be filtered out.

        Set this attribute to a sequence to change it, or to None to empty it.
        """)

    pass_extensions = Attribute(
        """Sequence of file extensions to explicitly pass.

        Set this attribute to a sequence to change it, or to None to empty it.
        Pass extensions are consulted after filter extensions, and only if
        `pass_extensions` is non-empty.
        """)
        



class IAcceptableAlias(Interface):
    """An acceptable alias for implicit destinations."""

    mailing_list = Attribute('The associated mailing list.')

    address = Attribute('The address or pattern to match against recipients.')


class IAcceptableAliasSet(Interface):
    """The set of acceptable aliases for a mailing list."""

    def clear():
        """Clear the set of acceptable posting aliases."""

    def add(alias):
        """Add the given address as an acceptable aliases for posting.

        :param alias: The email address to accept as a recipient for implicit
            destination posting purposes.  The alias is coerced to lower
            case.  If `alias` begins with a '^' character, it is interpreted
            as a regular expression, otherwise it must be an email address.
        :type alias: string
        :raises ValueError: when the alias neither starts with '^' nor has an
            '@' sign in it.
        """

    def remove(alias):
        """Remove the given address as an acceptable aliases for posting.

        :param alias: The email address to no longer accept as a recipient for
            implicit destination posting purposes.
        :type alias: string
        """

    aliases = Attribute(
        """An iterator over all the acceptable aliases.""")
