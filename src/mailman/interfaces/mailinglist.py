# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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
    'IAcceptableAlias',
    'IAcceptableAliasSet',
    'IMailingList',
    'Personalization',
    'ReplyToMunging',
    ]


from flufl.enum import Enum
from zope.interface import Interface, Attribute

from mailman.interfaces.member import MemberRole



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

    # List identity

    created_at = Attribute(
        """The date and time that the mailing list was created.""")

    list_name = Attribute("""\
        The read-only short name of the mailing list.  Note that where a
        Mailman installation supports multiple domains, this short name may
        not be unique.  Use the fqdn_listname attribute for a guaranteed
        unique id for the mailing list.  This short name is always the local
        part of the posting email address.  For example, if messages are
        posted to mylist@example.com, then the list_name is 'mylist'.
        """)

    mail_host = Attribute("""\
        The read-only domain name 'hosting' this mailing list.  This is always
        the domain name part of the posting email address, and it may bear no
        relationship to the web url used to access this mailing list.  For
        example, if messages are posted to mylist@example.com, then the
        mail_host is 'example.com'.
        """)

    fqdn_listname = Attribute("""\
        The read-only fully qualified name of the mailing list.  This is the
        guaranteed unique id for the mailing list, and it is always the
        address to which messages are posted, e.g. mylist@example.com.  It is
        always comprised of the list_name + '@' + mail_host.
        """)

    domain = Attribute(
        """The `IDomain` that this mailing list is defined in.""")

    display_name = Attribute("""\
        The short human-readable descriptive name for the mailing list.  This
        is used in locations such as the message footers and Subject prefix.
        """)

    description = Attribute("""\
        A terse phrase identifying this mailing list.

        This description is used when the mailing list is listed with other
        mailing lists, or in headers, and so forth.  It should be as succinct
        as you can get it, while still identifying what the list is.""")

    include_list_post_header = Attribute(
        """Flag specifying whether to include the RFC 2369 List-Post header.
        This is usually set to True, except for announce-only lists.""")

    include_rfc2369_headers = Attribute(
        """Flag specifying whether to include any RFC 2369 header, including
        the RFC 2919 List-ID header.""")

    anonymous_list = Attribute(
        """Flag controlling whether messages to this list are anonymized.

        Anonymizing messages is not perfect, however setting this flag removes
        the sender of the message (in the From, Sender, and Reply-To fields)
        and replaces these with the list's posting address.
        """)

    advertised = Attribute(
        """Advertise this mailing list when people ask for an overview of the
        available mailing lists.""")

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
        """The address to which subscription requests should be sent.""")

    leave_address = Attribute(
        """The address to which unsubscription requests should be sent.""")

    subscribe_address = Attribute(
        """Deprecated address to which subscription requests may be sent.
        This address is provided for backward compatibility only.  See
        `join_address` for the preferred alias.
        """)

    unsubscribe_address = Attribute(
        """Deprecated address to which unsubscription requests may be sent.
        This address is provided for backward compatibility only.  See
        `leave_address` for the preferred alias.
        """)

    def confirm_address(cookie=''):
        """The address used for various forms of email confirmation."""

    # Rosters and subscriptions.

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

    def get_roster(role):
        """Return the appropriate roster for the given role.

        :param role: The requested roster's role.
        :type role: MemberRole
        :return: The requested roster.
        :rtype: Roster
        """

    def subscribe(subscriber, role=MemberRole.member):
        """Subscribe the given address or user to the mailing list.

        :param subscriber: The address or user to subscribe to the mailing
            list.  The user's preferred address receives deliveries, if she
            has one, otherwise no address for the user appears in the rosters.
        :type subscriber: `IUser` or `IAddress`
        :param role: The role being subscribed to (e.g. a member, owner, or
            moderator of a mailing list.
        :type role: `MemberRole`
        :return: The member object representing the subscription.
        :rtype: `IMember`
        :raises AlreadySubscribedError: If the address or user is already
            subscribed to the mailing list with the given role.  Note however
            that it is possible to subscribe an address to a mailing list with
            a particular role, and also subscribe a user with a matching
            preferred address that is explicitly subscribed with the same role.
        """

    # Delivery.

    last_post_at = Attribute(
        """The date and time a message was last posted to the mailing list.""")

    post_id = Attribute(
        """A monotonically increasing integer sequentially assigned to each
        list posting.""")

    personalize = Attribute(
        """The type of personalization that is applied to postings.""")

    reply_goes_to_list = Attribute(
        """Reply-To: header munging policy.""")

    # Digests.

    digest_last_sent_at = Attribute(
        """The date and time a digest of this mailing list was last sent.""")

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

    # Web access.

    scheme = Attribute(
        """The protocol scheme used to contact this list's server.

        The web server on this protocol provides the web interface for this
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

    # Autoresponses.

    autoresponse_grace_period = Attribute(
        """Time period (in days) between automatic responses.

        When this mailing list is set to send an auto-response for messages
        sent to mailing list posts, the mailing list owners, or the `-request`
        address, such reponses will not be sent to the same user more than
        once during the grace period.  Set to zero (or a negative value) for
        no grace period (i.e. auto-respond to every message).
        """)

    autorespond_owner = Attribute(
        """How should the mailing list automatically respond to messages sent
        to the -owner or -moderator address?

        Options are:
        * No response sent
        * Send a response and discard the original messge
        * Send a response and continue processing the original message
        """)

    autoresponse_owner_text = Attribute(
        """The text sent in an autoresponse to the owner or moderator.""")

    autorespond_postings = Attribute(
        """How should the mailing list automatically respond to messages sent
        to the list's posting address?

        Options are:
        * No response sent
        * Send a response and discard the original messge
        * Send a response and continue processing the original message
        """)

    autoresponse_postings_text = Attribute(
        """The text sent in an autoresponse to the list's posting address.""")

    autorespond_requests = Attribute(
        """How should the mailing list automatically respond to messages sent
        to the list's `-request` address?

        Options are:
        * No response sent
        * Send a response and discard the original messge
        * Send a response and continue processing the original message
        """)

    autoresponse_request_text = Attribute(
        """The text sent in an autoresponse to the list's `-request`
        address.""")

    # Processing.

    posting_chain = Attribute(
        """This mailing list's posting moderation chain.

        When messages are posted to a mailing list, it first goes through a
        moderation chain to determine whether the message will be accepted.
        This attribute names a chain for postings, which must exist.
        """)

    posting_pipeline = Attribute(
        """This mailing list's posting pipeline.

        Every mailing list has a processing pipeline that messages flow
        through once they've been accepted for posting to the mailing list.
        This attribute names a pipeline for postings, which must exist.
        """)

    owner_chain = Attribute(
        """This mailing list's owner moderation chain.

        When messages are posted to the owners of a mailing list, it first
        goes through a moderation chain to determine whether the message will
        be accepted.  This attribute names a chain for postings, which must
        exist.
        """)

    owner_pipeline = Attribute(
        """This mailing list's owner posting pipeline.

        Every mailing list has a processing pipeline that messages flow
        through once they've been accepted for posting to the owners of a
        mailing list.  This attribute names a pipeline for postings, which
        must exist.
        """)

    data_path = Attribute(
        """The file system path to list-specific data.

        An example of list-specific data is the temporary digest mbox file
        that gets created to accumlate messages for the digest.
        """)

    administrative = Attribute(
        """Flag controlling `administrivia` checks.

        Administrivia tests check whether postings to the mailing list are
        really meant for the -request address.  Examples include messages with
        `help`, `subscribe`, `unsubscribe`, and other commands.  When such
        messages are incorrectly posted to the general mailing list, they are
        just noise, and when this flag is set will be intercepted and in
        general held for moderator approval.
        """)

    filter_content = Attribute(
        """Flag specifying whether to filter a message's content.

        Filtering is performed on MIME type and file name extension.
        """)

    filter_action = Attribute(
        """Action to take when the top-level content-type is filtered.

        The value is a `FilterAction` enum.
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

    # Moderation.

    default_member_action = Attribute(
        """The default action to take for postings from members.

        When an address is subscribed to the mailing list, this attribute sets
        the initial moderation action (as an `Action`).  When the action is
        `Action.defer` (the default), then normal posting decisions are made.
        When the action is `Action.accept`, the postings are accepted without
        any other checks.
        """)

    default_nonmember_action = Attribute(
        """The default action to take for postings from nonmembers.

        When a nonmember address posts to the mailing list, this attribute
        sets the initial moderation action (as an `Action`).  When the action
        is `Action.defer` (the default), then normal posting decisions are
        made.  When the action is `Action.accept`, the postings are accepted
        without any other checks.
        """)

    # Bounces.

    forward_unrecognized_bounces_to = Attribute(
        """What to do when a bounce contains no recognizable addresses.

        This is an enumeration which specifies what to do with such bounce
        messages.  They can be discarded, forward to the list owner, or
        forwarded to the site owner.
        """)

    process_bounces = Attribute(
        """Whether or not the mailing list processes bounces.""")

    # Notifications.

    admin_immed_notify = Attribute(
        """Flag controlling immediate notification of requests.

        List moderators normally get daily notices about pending
        administrative requests.  This flag controls whether moderators also
        receive immediate notification of such pending requests.
        """)

    admin_notify_mchanges = Attribute(
        """Flag controlling notification of joins and leaves.

        List moderators can receive notifications for every member that joins
        or leaves their mailing lists.  This flag controls those
        notifications.
        """)

    send_welcome_message = Attribute(
        """Flag indicating whether a welcome message should be sent.""")

    welcome_message_uri = Attribute(
        """URI for the list's welcome message.

        This can be any URI supported by `urllib2` with the addition of
        `mailman:` URIs, which reference internal default resources.  This is
        a template which can include the following placeholders:

        $listname - the FQDN list name for this mailing list.
        $language - the language code, usually the list's preferred language.

        The resource will be downloaded and cached whenever the welcome
        message is sent.  The resource at this URI can contain the following
        placeholders, which are also filled in through values on the mailing
        list:

        $fqdn_listname    - the FQDN list name for this mailing list.
        $list_name        - the human readable name for the mailing list.
        $listinfo_uri     - the URI to the list's information page.
        $list_requests    - the address to the list's `-request` address.
        $user_name        - the name of the subscribing user.
        $user_address     - the email address of the subscribing user.
        $user_options_uri - the URI to this member's options page.
        """)

    send_goodbye_message = Attribute(
        """Flag indicating whether a goodbye message should be sent.""")

    goodbye_message_uri = Attribute(
        """URI for the list's goodbye message.

        This can be any URI supported by `urllib2` with the addition of
        `mailman:` URIs, which reference internal default resources.  This is
        a template which can include the following placeholders:

        $listname - the FQDN list name for this mailing list.
        $language - the language code, usually the list's preferred language.

        The resource will be downloaded and cached whenever the goodbye
        message is sent.  The resource at this URI can contain the following
        placeholders, which are also filled in through values on the mailing
        list:

        $fqdn_listname    - the FQDN list name for this mailing list.
        $list_name        - the human readable name for the mailing list.
        $listinfo_uri     - the URI to the list's information page.
        $list_requests    - the address to the list's `-request` address.
        $user_name        - the name of the subscribing user.
        $user_address     - the email address of the subscribing user.
        $user_options_uri - the URI to this member's options page.
        """)

    # Decorators.

    header_uri = Attribute(
        """URI for the header decorator on regular delivery messages.

        This can be any URI supported by `urllib2` with the addition of
        `mailman:` URIs, which reference internal default resources.  This is
        a template which can include the following placeholders:

        $listname - the FQDN list name for this mailing list.
        $language - the language code, usually the list's preferred language.

        The resource will be downloaded and cached whenever the decorator is
        needed.  The resource at this URI can contain the following
        placeholders, which are also filled in through values on the mailing
        list:

        $fqdn_listname    - the FQDN list name for this mailing list.
        $list_name        - the human readable name for the mailing list.
        $host_name        - the mailing list's host name
        $listinfo_uri     - the URI to the list's information page.
        $list_requests    - the address to the list's `-request` address.
        $description      - the mailing list's description
        $info             - additional mailing list's information

        Personalized messages will also have these placeholders available:

        $user_name        - the name of the subscribing user.
        $user_address     - the email address of the subscribing user.
        $user_options_uri - the URI to this member's options page.
        """
        )

    footer_uri = Attribute(
        """URI for the footer decorator on regular delivery messages.

        This can be any URI supported by `urllib2` with the addition of
        `mailman:` URIs, which reference internal default resources.  This is
        a template which can include the following placeholders:

        $listname - the FQDN list name for this mailing list.
        $language - the language code, usually the list's preferred language.

        The resource will be downloaded and cached whenever the decorator is
        needed.  The resource at this URI can contain the following
        placeholders, which are also filled in through values on the mailing
        list:

        $fqdn_listname    - the FQDN list name for this mailing list.
        $list_name        - the human readable name for the mailing list.
        $host_name        - the mailing list's host name
        $listinfo_uri     - the URI to the list's information page.
        $list_requests    - the address to the list's `-request` address.
        $description      - the mailing list's description
        $info             - additional mailing list's information

        Personalized messages will also have these placeholders available:

        $user_name        - the name of the subscribing user.
        $user_address     - the email address of the subscribing user.
        $user_options_uri - the URI to this member's options page.
        """
        )

    digest_header_uri = Attribute(
        """URI for the header decorator on digest messages.

        This can be any URI supported by `urllib2` with the addition of
        `mailman:` URIs, which reference internal default resources.  This is
        a template which can include the following placeholders:

        $listname - the FQDN list name for this mailing list.
        $language - the language code, usually the list's preferred language.

        The resource will be downloaded and cached whenever the decorator is
        needed.  The resource at this URI can contain the following
        placeholders, which are also filled in through values on the mailing
        list:

        $fqdn_listname    - the FQDN list name for this mailing list.
        $list_name        - the human readable name for the mailing list.
        $host_name        - the mailing list's host name
        $listinfo_uri     - the URI to the list's information page.
        $list_requests    - the address to the list's `-request` address.
        $description      - the mailing list's description
        $info             - additional mailing list's information

        Personalized messages will also have these placeholders available:

        $user_name        - the name of the subscribing user.
        $user_address     - the email address of the subscribing user.
        $user_options_uri - the URI to this member's options page.
        """
        )

    digest_footer_uri = Attribute(
        """URI for the footer decorator on digest messages.

        This can be any URI supported by `urllib2` with the addition of
        `mailman:` URIs, which reference internal default resources.  This is
        a template which can include the following placeholders:

        $listname - the FQDN list name for this mailing list.
        $language - the language code, usually the list's preferred language.

        The resource will be downloaded and cached whenever the decorator is
        needed.  The resource at this URI can contain the following
        placeholders, which are also filled in through values on the mailing
        list:

        $fqdn_listname    - the FQDN list name for this mailing list.
        $list_name        - the human readable name for the mailing list.
        $host_name        - the mailing list's host name
        $listinfo_uri     - the URI to the list's information page.
        $list_requests    - the address to the list's `-request` address.
        $description      - the mailing list's description
        $info             - additional mailing list's information

        Personalized messages will also have these placeholders available:

        $user_name        - the name of the subscribing user.
        $user_address     - the email address of the subscribing user.
        $user_options_uri - the URI to this member's options page.
        """
        )



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
