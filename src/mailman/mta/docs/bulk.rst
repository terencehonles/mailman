======================
Standard bulk delivery
======================

Mailman has several built in strategies for completing the actual delivery of
messages to the immediate upstream mail transport agent, which completes the
actual final delivery to recipients.

Bulk delivery attempts to deliver as few copies of the identical message as
possible to as many recipients as possible.  By grouping recipients this way,
bandwidth between Mailman and the MTA, and consequently between the MTA and
remote mail servers, can be greatly reduced.  The downside is the messages
cannot be personalized.  See `verp.txt`_ for an alternative strategy.

    >>> from mailman.mta.bulk import BulkDelivery

The standard bulk deliverer takes as an argument the maximum number of
recipients per session.  The default is to deliver the message in one chunk,
containing all recipients.

    >>> bulk = BulkDelivery()

Delivery strategies must implement the proper interface.

    >>> from mailman.interfaces.mta import IMailTransportAgentDelivery
    >>> from zope.interface.verify import verifyObject
    >>> verifyObject(IMailTransportAgentDelivery, bulk)
    True


Chunking recipients
===================

The set of final recipients is contained in the ``recipients`` key in the
message metadata.  When ``max_recipients`` is specified as zero, then the bulk
deliverer puts all recipients into one big chunk.
::

    >>> from string import ascii_letters
    >>> recipients = set(letter + 'person@example.com'
    ...                  for letter in ascii_letters)

    >>> chunks = list(bulk.chunkify(recipients))
    >>> len(chunks)
    1
    >>> len(chunks[0])
    52

Let say the maximum number of recipients allowed is 4, then no chunk will have
more than 4 recipients, though they can have fewer (but still not zero).

    >>> bulk = BulkDelivery(4)
    >>> chunks = list(bulk.chunkify(recipients))
    >>> len(chunks)
    13
    >>> all(0 < len(chunk) <= 4 for chunk in chunks)
    True

The chunking algorithm sorts recipients by top level domain by length.
::

    >>> recipients = set([
    ...     'anne@example.com',
    ...     'bart@example.org',
    ...     'cate@example.net',
    ...     'dave@example.com',
    ...     'elle@example.org',
    ...     'fred@example.net',
    ...     'gwen@example.com',
    ...     'herb@example.us',
    ...     'ione@example.net',
    ...     'john@example.com',
    ...     'kate@example.com',
    ...     'liam@example.ca',
    ...     'mary@example.us',
    ...     'neil@example.net',
    ...     'ocho@example.org',
    ...     'paco@example.xx',
    ...     'quaq@example.zz',
    ...     ])

    >>> bulk = BulkDelivery(4)
    >>> chunks = list(bulk.chunkify(recipients))
    >>> len(chunks)
    6

We can't make any guarantees about sorting within each chunk, but we can tell
a few things.  For example, the first two chunks will be composed of ``.net``
(4) and ``.org`` (3) domains (for a total of 7).
::

    >>> len(chunks[0])
    4
    >>> len(chunks[1])
    3

    >>> for address in sorted(chunks[0].union(chunks[1])):
    ...     print address
    bart@example.org
    cate@example.net
    elle@example.org
    fred@example.net
    ione@example.net
    neil@example.net
    ocho@example.org

We also know that the next two chunks will contain ``.com`` (5) addresses.
::

    >>> len(chunks[2])
    4
    >>> len(chunks[3])
    1

    >>> for address in sorted(chunks[2].union(chunks[3])):
    ...     print address
    anne@example.com
    dave@example.com
    gwen@example.com
    john@example.com
    kate@example.com

The next chunk will contain the ``.us`` (2) and ``.ca`` (1) domains.

    >>> len(chunks[4])
    3
    >>> for address in sorted(chunks[4]):
    ...     print address
    herb@example.us
    liam@example.ca
    mary@example.us

The final chunk will contain the outliers, ``.xx`` (1) and ``.zz`` (2).
::

    >>> len(chunks[5])
    2
    >>> for address in sorted(chunks[5]):
    ...     print address
    paco@example.xx
    quaq@example.zz


Bulk delivery
=============

The set of recipients for bulk delivery comes from the message metadata.  If
there are no calculated recipients, nothing gets sent.
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

    >>> bulk = BulkDelivery()
    >>> bulk.deliver(mlist, msg, {})
    {}
    >>> len(list(smtpd.messages))
    0

    >>> bulk.deliver(mlist, msg, dict(recipients=set()))
    {}
    >>> len(list(smtpd.messages))
    0

With bulk delivery and no maximum number of recipients, there will be just one
message sent, with all the recipients packed into the envelope recipients
(i.e. ``RCTP TO``).
::

    >>> recipients = set('person_{0:02d}'.format(i) for i in range(100))
    >>> msgdata = dict(recipients=recipients)
    >>> bulk.deliver(mlist, msg, msgdata)
    {}

    >>> messages = list(smtpd.messages)
    >>> len(messages)
    1
    >>> print messages[0].as_string()
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    ...
    X-RcptTo: person_...
        person_...
    ...
    <BLANKLINE>
    This is a test.

The ``X-RcptTo:`` header contains the set of recipients, in random order.

    >>> len(messages[0]['x-rcptto'].split(','))
    100

When the maximum number of recipients is set to 20, 5 messages will be sent,
each with 20 addresses in the ``RCPT TO``.
::

    >>> bulk = BulkDelivery(20)
    >>> bulk.deliver(mlist, msg, msgdata)
    {}

    >>> messages = list(smtpd.messages)
    >>> len(messages)
    5
    >>> for message in messages:
    ...     x_rcptto = message['x-rcptto']
    ...     print 'Number of recipients:', len(x_rcptto.split(','))
    Number of recipients: 20
    Number of recipients: 20
    Number of recipients: 20
    Number of recipients: 20
    Number of recipients: 20


Delivery headers
================

The sending agent shows up in the RFC 5321 ``MAIL FROM``, which shows up in
the ``X-MailFrom:`` header in the sample message.

The bulk delivery module calculates the sending agent address first from the
message metadata...
::

    >>> bulk = BulkDelivery()
    >>> recipients = set(['aperson@example.com'])
    >>> msgdata = dict(recipients=recipients,
    ...                sender='asender@example.org')
    >>> bulk.deliver(mlist, msg, msgdata)
    {}

    >>> message = list(smtpd.messages)[0]
    >>> print message.as_string()
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: asender@example.org
    X-RcptTo: aperson@example.com
    <BLANKLINE>
    This is a test.

...followed by the mailing list's bounces robot address...
::

    >>> del msgdata['sender']
    >>> bulk.deliver(mlist, msg, msgdata)
    {}

    >>> message = list(smtpd.messages)[0]
    >>> print message.as_string()
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: aperson@example.com
    <BLANKLINE>
    This is a test.

...and finally the site owner, if there is no mailing list target for this
message.
::

    >>> config.push('site-owner', """\
    ... [mailman]
    ... site_owner: site-owner@example.com
    ... """)

    >>> bulk.deliver(None, msg, msgdata)
    {}

    >>> message = list(smtpd.messages)[0]
    >>> print message.as_string()
    From: aperson@example.org
    To: test@example.com
    Subject: test one
    Message-ID: <aardvark>
    X-Peer: ...
    X-MailFrom: site-owner@example.com
    X-RcptTo: aperson@example.com
    <BLANKLINE>
    This is a test.

    # Remove test configuration.
    >>> config.pop('site-owner')


Delivery failures
=================

Mailman does not do final delivery.  Instead, it sends mail through a site
local mail server which manages queuing and final delivery.  However, even
this local mail server can produce delivery failures visible to Mailman in
certain situations.

For example, there could be a problem delivering to any of the specified
recipients.
::

    # Tell the mail server to fail on the next 3 RCPT TO commands, one for
    # each recipient in the following message.
    >>> smtpd.err_queue.put(('rcpt', 500))
    >>> smtpd.err_queue.put(('rcpt', 500))
    >>> smtpd.err_queue.put(('rcpt', 500))

    >>> recipients = set([
    ...     'aperson@example.org',
    ...     'bperson@example.org',
    ...     'cperson@example.org',
    ...     ])
    >>> msgdata = dict(recipients=recipients)

    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... To: test@example.com
    ... Subject: test three
    ... Message-ID: <camel>
    ...
    ... This is a test.
    ... """)

    >>> failures = bulk.deliver(mlist, msg, msgdata)
    >>> for address in sorted(failures):
    ...     print address, failures[address][0], failures[address][1]
    aperson@example.org 500 Error: SMTPRecipientsRefused
    bperson@example.org 500 Error: SMTPRecipientsRefused
    cperson@example.org 500 Error: SMTPRecipientsRefused

    >>> messages = list(smtpd.messages)
    >>> len(messages)
    0

Or there could be some other problem causing an SMTP response failure.
::

    # Tell the mail server to register a temporary failure on the next MAIL
    # FROM command.
    >>> smtpd.err_queue.put(('mail', 450))

    >>> failures = bulk.deliver(mlist, msg, msgdata)
    >>> for address in sorted(failures):
    ...     print address, failures[address][0], failures[address][1]
    aperson@example.org 450 Error: SMTPResponseException
    bperson@example.org 450 Error: SMTPResponseException
    cperson@example.org 450 Error: SMTPResponseException

    # Tell the mail server to register a permanent failure on the next MAIL
    # FROM command.
    >>> smtpd.err_queue.put(('mail', 500))

    >>> failures = bulk.deliver(mlist, msg, msgdata)
    >>> for address in sorted(failures):
    ...     print address, failures[address][0], failures[address][1]
    aperson@example.org 500 Error: SMTPResponseException
    bperson@example.org 500 Error: SMTPResponseException
    cperson@example.org 500 Error: SMTPResponseException

XXX Untested: socket.error, IOError, smtplib.SMTPException.

.. _verp.txt: verp.html
