======================
Standard VERP delivery
======================

Variable Envelope Return Path (VERP_) delivery is an alternative to bulk_
delivery, where an individual message is crafted uniquely for each recipient.

The cost of enabling VERP is that Mailman must send to the upstream MTA, one
message per recipient.  Under bulk delivery, an exact copy of one message can
be sent to many recipients, greatly reducing the bandwidth for delivery.

In Mailman, enabling VERP delivery for bounce detection brings with it a side
benefit: the message which must be crafted uniquely for each recipient, can be
further personalized to include all kinds of information unique to that
recipient.  In the simplest case, the message can contain footer information,
e.g.  pointing the user to their account URL or including a user-specific
unsubscription link.  In theory, VERP delivery means we can do sophisticated
`mail merge`_ operations.

Mailman's use of the term VERP really means *message personalization*.

    >>> from mailman.mta.verp import VERPDelivery
    >>> verp = VERPDelivery()

Delivery strategies must implement the proper interface.

    >>> from mailman.interfaces.mta import IMailTransportAgentDelivery
    >>> from zope.interface.verify import verifyObject
    >>> verifyObject(IMailTransportAgentDelivery, verp)
    True


No recipients
=============

The message metadata specifies the set of recipients to send this message to.
If there are no recipients, there's nothing to do.
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

    >>> verp.deliver(mlist, msg, {})
    {}
    >>> len(list(smtpd.messages))
    0

    >>> verp.deliver(mlist, msg, dict(recipients=set()))
    {}
    >>> len(list(smtpd.messages))
    0


Individual copy
===============

Each recipient of the message gets an individual, personalized copy of the
message, with their email address encoded into the envelope sender.  This is
so the return path will point back to Mailman but allow for decoding of the
intended recipient's delivery address.

    >>> recipients = set([
    ...     'aperson@example.com',
    ...     'bperson@example.com',
    ...     'cperson@example.com',
    ...     ])

VERPing is only actually done if the metadata requests it.
::

    >>> msgdata = dict(recipients=recipients, verp=True)
    >>> verp.deliver(mlist, msg, msgdata)
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
    X-MailFrom: test-bounces+aperson=example.com@example.com
    X-RcptTo: aperson@example.com
    <BLANKLINE>
    This is a test.
    ----------
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces+bperson=example.com@example.com
    X-RcptTo: bperson@example.com
    <BLANKLINE>
    This is a test.
    ----------
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces+cperson=example.com@example.com
    X-RcptTo: cperson@example.com
    <BLANKLINE>
    This is a test.
    ----------

The deliverer made a copy of the original message, so it wasn't changed.

    >>> print msg.as_string()
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    <BLANKLINE>
    This is a test.
    <BLANKLINE>


.. _VERP: http://en.wikipedia.org/wiki/Variable_envelope_return_path
.. _bulk: bulk.html
.. _`mail merge`: http://en.wikipedia.org/wiki/Mail_merge
