==========
Moderation
==========

All members and nonmembers have a moderation action.  When the action is not
`defer`, the `moderation` rule flags the message as needing moderation.  This
might be to automatically accept, discard, reject, or hold the message.

Two separate rules check for member and nonmember moderation.  Member
moderation happens early in the built-in chain, while nonmember moderation
happens later in the chain, after normal moderation checks.

    >>> mlist = create_list('test@example.com')


Member moderation
=================

    >>> member_rule = config.rules['member-moderation']
    >>> print member_rule.name
    member-moderation

Anne, a mailing list member, sends a message to the mailing list.  Her
postings are not moderated.
::

    >>> from mailman.testing.helpers import subscribe
    >>> subscribe(mlist, 'Anne')
    >>> member = mlist.members.get_member('aperson@example.com')
    >>> print member.moderation_action
    Action.defer

Because Anne is not moderated, the member moderation rule does not match.

    >>> member_msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> member_rule.check(mlist, member_msg, {})
    False

Once the member's moderation action is set to something other than `defer`,
the rule matches.  Also, the message metadata has a few extra pieces of
information for the eventual moderation chain.

    >>> from mailman.interfaces.action import Action
    >>> member.moderation_action = Action.hold
    >>> msgdata = {}
    >>> member_rule.check(mlist, member_msg, msgdata)
    True
    >>> dump_msgdata(msgdata)
    moderation_action: hold
    moderation_sender: aperson@example.com


Nonmembers
==========

Nonmembers are handled in a similar way, although by default, nonmember
postings are held for moderator approval.

    >>> nonmember_rule = config.rules['nonmember-moderation']
    >>> print nonmember_rule.name
    nonmember-moderation

Bart, who is not a member of the mailing list, sends a message to the list.

    >>> from mailman.interfaces.member import MemberRole
    >>> subscribe(mlist, 'Bart', MemberRole.nonmember)
    >>> nonmember = mlist.nonmembers.get_member('bperson@example.com')
    >>> print nonmember.moderation_action
    Action.hold

When Bart is registered as a nonmember of the list, his moderation action is
set to hold by default.  Thus the rule matches and the message metadata again
carries some useful information.

    >>> nonmember_msg = message_from_string("""\
    ... From: bperson@example.com
    ... To: test@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> msgdata = {}
    >>> nonmember_rule.check(mlist, nonmember_msg, msgdata)
    True
    >>> dump_msgdata(msgdata)
    moderation_action: hold
    moderation_sender: bperson@example.com

Of course, the nonmember action can be set to defer the decision, in which
case the rule does not match.

    >>> nonmember.moderation_action = Action.defer
    >>> nonmember_rule.check(mlist, nonmember_msg, {})
    False


Unregistered nonmembers
=======================

The incoming runner ensures that all sender addresses are registered in the
system, but it is the moderation rule that subscribes nonmember addresses to
the mailing list if they are not already subscribed.
::

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> address = getUtility(IUserManager).create_address(
    ...     'cperson@example.com')
    >>> address
    <Address: cperson@example.com [not verified] at ...>

    >>> msg = message_from_string("""\
    ... From: cperson@example.com
    ... To: test@example.com
    ... Subject: A posted message
    ...
    ... """)

cperson is neither a member, nor a nonmember of the mailing list.
::

    >>> def memberkey(member):
    ...     return member.mailing_list, member.address.email, int(member.role)

    >>> dump_list(mlist.members.members, key=memberkey)
    <Member: Anne Person <aperson@example.com>
             on test@example.com as MemberRole.member>
    >>> dump_list(mlist.nonmembers.members, key=memberkey)
    <Member: Bart Person <bperson@example.com>
             on test@example.com as MemberRole.nonmember>

However, when the nonmember moderation rule runs, it adds the cperson as a
nonmember of the list.  The rule also matches.

    >>> msgdata = {}
    >>> nonmember_rule.check(mlist, msg, msgdata)
    True
    >>> dump_msgdata(msgdata)
    moderation_action: hold
    moderation_sender: cperson@example.com

    >>> dump_list(mlist.members.members, key=memberkey)
    <Member: Anne Person <aperson@example.com>
             on test@example.com as MemberRole.member>
    >>> dump_list(mlist.nonmembers.members, key=memberkey)
    <Member: Bart Person <bperson@example.com>
             on test@example.com as MemberRole.nonmember>
    <Member: cperson@example.com
             on test@example.com as MemberRole.nonmember>


Cross-membership checks
=======================

Of course, the member moderation rule does not match for nonmembers...

    >>> member_rule.check(mlist, nonmember_msg, {})
    False
    >>> nonmember_rule.check(mlist, member_msg, {})
    False
