======================
Message acknowledgment
======================

When a user posts a message to a mailing list, and that user has chosen to
receive acknowledgments of their postings, Mailman will sent them such an
acknowledgment.
::

    >>> mlist = create_list('test@example.com')
    >>> mlist.display_name = 'Test'
    >>> mlist.preferred_language = 'en'
    >>> # XXX This will almost certainly change once we've worked out the web
    >>> # space layout for mailing lists now.

    >>> # Ensure that the virgin queue is empty, since we'll be checking this
    >>> # for new auto-response messages.
    >>> from mailman.testing.helpers import get_queue_messages
    >>> get_queue_messages('virgin')
    []

Subscribe a user to the mailing list.
::

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)

    >>> from mailman.interfaces.member import MemberRole
    >>> user_1 = user_manager.create_user('aperson@example.com')
    >>> address_1 = list(user_1.addresses)[0]
    >>> mlist.subscribe(address_1, MemberRole.member)
    <Member: aperson@example.com on test@example.com as MemberRole.member>


Non-member posts
================

Non-members can't get acknowledgments of their posts to the mailing list.
::

    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ...
    ... """)

    >>> handler = config.handlers['acknowledge']
    >>> handler.process(mlist, msg, {})
    >>> get_queue_messages('virgin')
    []

We can also specify the original sender in the message's metadata.  If that
person is also not a member, no acknowledgment will be sent either.

    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ...
    ... """)
    >>> handler.process(mlist, msg,
    ...     dict(original_sender='cperson@example.com'))
    >>> get_queue_messages('virgin')
    []


No acknowledgment requested
===========================

Unless the user has requested acknowledgments, they will not get one.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... """)
    >>> handler.process(mlist, msg, {})
    >>> get_queue_messages('virgin')
    []

Similarly if the original sender is specified in the message metadata, and
that sender is a member but not one who has requested acknowledgments, none
will be sent.
::

    >>> user_2 = user_manager.create_user('dperson@example.com')
    >>> address_2 = list(user_2.addresses)[0]
    >>> mlist.subscribe(address_2, MemberRole.member)
    <Member: dperson@example.com on test@example.com as MemberRole.member>

    >>> handler.process(mlist, msg,
    ...     dict(original_sender='dperson@example.com'))
    >>> get_queue_messages('virgin')
    []


Requested acknowledgments
=========================

If the member requests acknowledgments, Mailman will send them one when they
post to the mailing list.

    >>> user_1.preferences.acknowledge_posts = True

The receipt will include the original message's subject in the response body,

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: Something witty and insightful
    ...
    ... """)
    >>> handler.process(mlist, msg, {})
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg           : False
    listname            : test@example.com
    nodecorate          : True
    recipients          : set([u'aperson@example.com'])
    reduced_list_headers: True
    ...
    >>> print messages[0].msg.as_string()
    ...
    MIME-Version: 1.0
    ...
    Subject: Test post acknowledgment
    From: test-bounces@example.com
    To: aperson@example.com
    ...
    Precedence: bulk
    <BLANKLINE>
    Your message entitled
    <BLANKLINE>
        Something witty and insightful
    <BLANKLINE>
    was successfully received by the Test mailing list.
    <BLANKLINE>
    List info page: http://lists.example.com/listinfo/test@example.com
    Your preferences: http://example.com/aperson@example.com
    <BLANKLINE>

If there is no subject, then the receipt will use a generic message.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... """)
    >>> handler.process(mlist, msg, {})
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg           : False
    listname            : test@example.com
    nodecorate          : True
    recipients          : set([u'aperson@example.com'])
    reduced_list_headers: True
    ...
    >>> print messages[0].msg.as_string()
    MIME-Version: 1.0
    ...
    Subject: Test post acknowledgment
    From: test-bounces@example.com
    To: aperson@example.com
    ...
    Precedence: bulk
    <BLANKLINE>
    Your message entitled
    <BLANKLINE>
        (no subject)
    <BLANKLINE>
    was successfully received by the Test mailing list.
    <BLANKLINE>
    List info page: http://lists.example.com/listinfo/test@example.com
    Your preferences: http://example.com/aperson@example.com
    <BLANKLINE>
