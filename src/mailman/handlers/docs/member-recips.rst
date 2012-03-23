======================
Calculating recipients
======================

Every message that makes it through to the list membership gets sent to a set
of recipient addresses.  These addresses are calculated by one of the handler
modules and depends on a host of factors.

    >>> mlist = create_list('test@example.com')

Recipients are calculate from the list membership, so first some people
subscribe to the mailing list...
::

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)

    >>> address_a = user_manager.create_address('aperson@example.com')
    >>> address_b = user_manager.create_address('bperson@example.com')
    >>> address_c = user_manager.create_address('cperson@example.com')
    >>> address_d = user_manager.create_address('dperson@example.com')
    >>> address_e = user_manager.create_address('eperson@example.com')
    >>> address_f = user_manager.create_address('fperson@example.com')

...then subscribe these addresses to the mailing list as members...

    >>> from mailman.interfaces.member import MemberRole
    >>> member_a = mlist.subscribe(address_a, MemberRole.member)
    >>> member_b = mlist.subscribe(address_b, MemberRole.member)
    >>> member_c = mlist.subscribe(address_c, MemberRole.member)
    >>> member_d = mlist.subscribe(address_d, MemberRole.member)
    >>> member_e = mlist.subscribe(address_e, MemberRole.member)
    >>> member_f = mlist.subscribe(address_f, MemberRole.member)

...then make some of the members digest members.

    >>> from mailman.interfaces.member import DeliveryMode
    >>> member_d.preferences.delivery_mode = DeliveryMode.plaintext_digests
    >>> member_e.preferences.delivery_mode = DeliveryMode.mime_digests
    >>> member_f.preferences.delivery_mode = DeliveryMode.summary_digests


Regular delivery recipients
===========================

Regular delivery recipients are those people who get messages from the list as
soon as they are posted.  In other words, these folks are not digest members.

    >>> msg = message_from_string("""\
    ... From: Xavier Person <xperson@example.com>
    ...
    ... Something of great import.
    ... """)
    >>> msgdata = {}
    >>> handler = config.handlers['member-recipients']
    >>> handler.process(mlist, msg, msgdata)
    >>> dump_list(msgdata['recipients'])
    aperson@example.com
    bperson@example.com
    cperson@example.com

Members can elect not to receive a list copy of their own postings.

    >>> member_c.preferences.receive_own_postings = False
    >>> msg = message_from_string("""\
    ... From: Claire Person <cperson@example.com>
    ...
    ... Something of great import.
    ... """)
    >>> msgdata = {}
    >>> handler.process(mlist, msg, msgdata)
    >>> dump_list(msgdata['recipients'])
    aperson@example.com
    bperson@example.com

Members can also elect not to receive a list copy of any message on which they
are explicitly named as a recipient.  However, see the `avoid duplicates`_
handler for details.


Digest recipients
=================

XXX Test various digest deliveries.


Urgent messages
===============

XXX Test various urgent deliveries:
    * test_urgent_moderator()
    * test_urgent_admin()
    * test_urgent_reject()


.. _`avoid duplicates`: avoid-duplicates.html
