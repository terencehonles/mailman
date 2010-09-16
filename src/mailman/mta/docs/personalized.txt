===========================
Fully personalized delivery
===========================

Fully personalized mail delivery is an enhancement over VERP_ delivery where
the ``To:`` field of the message is replaced with the recipient's address.  A
typical email message is sent to the mailing list's posting address and copied
to the list membership that way.  Some people like the more personal address.

Personalized delivery still does VERP.

    >>> from mailman.mta.personalized import PersonalizedDelivery
    >>> personalized = PersonalizedDelivery()

Delivery strategies must implement the proper interface.

    >>> from mailman.interfaces.mta import IMailTransportAgentDelivery
    >>> from zope.interface.verify import verifyObject
    >>> verifyObject(IMailTransportAgentDelivery, personalized)
    True


No personalization
==================

By default, the ``To:`` header is not personalized.
::

    >>> mlist = create_list('test@example.com')
    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... To: test@example.com
    ... Subject: test one
    ... Message-ID: <aardvark>
    ...
    ... This is a test.
    ... """)

    >>> recipients = set([
    ...     'aperson@example.com',
    ...     'bperson@example.com',
    ...     'cperson@example.com',
    ...     ])

    >>> personalized.deliver(mlist, msg, dict(recipients=recipients))
    {}
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> from operator import itemgetter
    >>> for message in sorted(messages, key=itemgetter('x-rcptto')):
    ...     print message.as_string()
    ...     print '----------'
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: aperson@example.com
    <BLANKLINE>
    This is a test.
    ----------
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: bperson@example.com
    <BLANKLINE>
    This is a test.
    ----------
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: cperson@example.com
    <BLANKLINE>
    This is a test.
    ----------


To header
=========

When the mailing list requests personalization, the ``To:`` header is replaced
with the recipient's address and name.
::

    >>> from mailman.interfaces.mailinglist import Personalization
    >>> mlist.personalize = Personalization.full
    >>> transaction.commit()

    >>> personalized.deliver(mlist, msg, dict(recipients=recipients))
    {}
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> for message in sorted(messages, key=itemgetter('to')):
    ...     print message.as_string()
    ...     print '----------'
    From: aperson@example.org
    To: aperson@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: aperson@example.com
    <BLANKLINE>
    This is a test.
    ----------
    From: aperson@example.org
    To: bperson@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: bperson@example.com
    <BLANKLINE>
    This is a test.
    ----------
    From: aperson@example.org
    To: cperson@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: cperson@example.com
    <BLANKLINE>
    This is a test.
    ----------

If the recipient is a user registered with Mailman, and the user has an
associated real name, then this name also shows up in the ``To:`` header.
::

    >>> from zope.component import getUtility
    >>> from mailman.interfaces.usermanager import IUserManager
    >>> user_manager = getUtility(IUserManager)

    >>> bill = user_manager.create_user('bperson@example.com', 'Bill Person')
    >>> cate = user_manager.create_user('cperson@example.com', 'Cate Person')
    >>> transaction.commit()

    >>> personalized.deliver(mlist, msg, dict(recipients=recipients))
    {}
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> from operator import itemgetter
    >>> for message in sorted(messages, key=itemgetter('x-rcptto')):
    ...     print message.as_string()
    ...     print '----------'
    From: aperson@example.org
    To: aperson@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: aperson@example.com
    <BLANKLINE>
    This is a test.
    ----------
    From: aperson@example.org
    To: Bill Person <bperson@example.com>
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: bperson@example.com
    <BLANKLINE>
    This is a test.
    ----------
    From: aperson@example.org
    To: Cate Person <cperson@example.com>
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: cperson@example.com
    <BLANKLINE>
    This is a test.
    ----------


.. _VERP: verp.html
