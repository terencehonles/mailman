==========
Moderation
==========

Posts by members and nonmembers are subject to moderation checks during
incoming processing.  Different situations can cause such posts to be held for
moderator approval.

    >>> mlist = create_list('test@example.com')

Members and nonmembers have a *moderation action* which can shortcut the
normal moderation checks.  The built-in chain does just a few checks first,
such as seeing if the message has a matching `Approved:` header, or if the
emergency flag has been set on the mailing list, or whether a mail loop has
been detected.

After those, the moderation action for the sender is checked.  Members
generally have a `defer` action, meaning the normal moderation checks are
done, but it is also common for first-time posters to have a `hold` action,
meaning that their messages are held for moderator approval for a while.

Nonmembers almost always have a `hold` action, though some mailing lists may
choose to set this default action to `discard`, meaning their posts would be
immediately thrown away.


Member moderation
=================

Posts by list members are moderated if the member's moderation action is not
deferred.  The default setting for the moderation action of new members is
determined by the mailing list's settings.  By default, a mailing list is not
set to moderate new member postings.

    >>> from mailman.app.membership import add_member
    >>> from mailman.interfaces.member import DeliveryMode
    >>> member = add_member(mlist, 'anne@example.com', 'Anne', 'aaa',
    ...                     DeliveryMode.regular, 'en')
    >>> member
    <Member: Anne <anne@example.com> on test@example.com as MemberRole.member>
    >>> print member.moderation_action
    Action.defer

In order to find out whether the message is held or accepted, we can subscribe
to Zope events that are triggered on each case.
::

    >>> from mailman.chains.base import ChainNotification
    >>> def on_chain(event):
    ...     if isinstance(event, ChainNotification):
    ...         print event
    ...         print event.chain
    ...         print 'Subject:', event.msg['subject']
    ...         print 'Hits:'
    ...         for hit in event.msgdata.get('rule_hits', []):
    ...             print '   ', hit
    ...         print 'Misses:'
    ...         for miss in event.msgdata.get('rule_misses', []):
    ...             print '   ', miss

Anne's post to the mailing list runs through the incoming runner's default
built-in chain.  No rules hit and so the message is accepted.
::

    >>> msg = message_from_string("""\
    ... From: anne@example.com
    ... To: test@example.com
    ... Subject: aardvark
    ...
    ... This is a test.
    ... """)

    >>> from mailman.core.chains import process
    >>> from mailman.testing.helpers import event_subscribers
    >>> with event_subscribers(on_chain):
    ...     process(mlist, msg, {}, 'built-in')
    <mailman.chains.accept.AcceptNotification ...>
    <mailman.chains.accept.AcceptChain ...>
    Subject: aardvark
    Hits:
    Misses:
        approved
        emergency
        loop
        member-moderation
        administrivia
        implicit-dest
        max-recipients
        max-size
        news-moderation
        no-subject
        suspicious-header
        nonmember-moderation

However, when Anne's moderation action is set to `hold`, her post is held for
moderator approval.
::

    >>> from mailman.interfaces.action import Action
    >>> member.moderation_action = Action.hold

    >>> msg = message_from_string("""\
    ... From: anne@example.com
    ... To: test@example.com
    ... Subject: badger
    ...
    ... This is a test.
    ... """)

    >>> with event_subscribers(on_chain):
    ...     process(mlist, msg, {}, 'built-in')
    <mailman.chains.hold.HoldNotification ...>
    <mailman.chains.hold.HoldChain ...>
    Subject: badger
    Hits:
        member-moderation
    Misses:
        approved
        emergency
        loop

The list's member moderation action can also be set to `discard`...
::

    >>> member.moderation_action = Action.discard

    >>> msg = message_from_string("""\
    ... From: anne@example.com
    ... To: test@example.com
    ... Subject: cougar
    ...
    ... This is a test.
    ... """)

    >>> with event_subscribers(on_chain):
    ...     process(mlist, msg, {}, 'built-in')
    <mailman.chains.discard.DiscardNotification ...>
    <mailman.chains.discard.DiscardChain ...>
    Subject: cougar
    Hits:
        member-moderation
    Misses:
        approved
        emergency
        loop

... or `reject`.

    >>> member.moderation_action = Action.reject

    >>> msg = message_from_string("""\
    ... From: anne@example.com
    ... To: test@example.com
    ... Subject: dingo
    ...
    ... This is a test.
    ... """)

    >>> with event_subscribers(on_chain):
    ...     process(mlist, msg, {}, 'built-in')
    <mailman.chains.reject.RejectNotification ...>
    <mailman.chains.reject.RejectChain ...>
    Subject: dingo
    Hits:
        member-moderation
    Misses:
        approved
        emergency
        loop


Nonmembers
==========

Registered nonmembers are handled very similarly to members, the main
difference being that they usually have a default moderation action.  This is
how the incoming runner adds sender addresses as nonmembers.

    >>> from zope.component import getUtility
    >>> from mailman.interfaces.usermanager import IUserManager
    >>> user_manager = getUtility(IUserManager)
    >>> address = user_manager.create_address('bart@example.com')
    >>> address
    <Address: bart@example.com [not verified] at ...>

When the moderation rule runs on a message from this sender, this address will
be registered as a nonmember of the mailing list, and it will be held for
moderator approval.
::

    >>> msg = message_from_string("""\
    ... From: bart@example.com
    ... To: test@example.com
    ... Subject: elephant
    ...
    ... """)

    >>> with event_subscribers(on_chain):
    ...     process(mlist, msg, {}, 'built-in')
    <mailman.chains.hold.HoldNotification ...>
    <mailman.chains.hold.HoldChain ...>
    Subject: elephant
    Hits:
        nonmember-moderation
    Misses:
        approved
        emergency
        loop
        member-moderation
        administrivia
        implicit-dest
        max-recipients
        max-size
        news-moderation
        no-subject
        suspicious-header

    >>> nonmember = mlist.nonmembers.get_member('bart@example.com')
    >>> nonmember
    <Member: bart@example.com on test@example.com as MemberRole.nonmember>
    >>> print nonmember.moderation_action
    Action.hold
