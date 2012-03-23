===========
LTMP server
===========

Mailman can accept messages via LMTP (RFC 2033).  Most modern mail servers
support LMTP local delivery, so this is a very portable way to connect Mailman
with your mail server.

Our LMTP server is fairly simple though; all it does is make sure that the
message is destined for a valid endpoint, e.g. ``mylist-join@example.com``,
that the message bytes can be parsed into a message object, and that the
message has a `Message-ID` header.

Let's start a testable LMTP runner.

    >>> from mailman.testing import helpers
    >>> master = helpers.TestableMaster()
    >>> master.start('lmtp')

It also helps to have a nice LMTP client.

    >>> lmtp = helpers.get_lmtp_client()
    (220, '... Python LMTP runner 1.0')
    >>> lmtp.lhlo('remote.example.org')
    (250, ...)


Posting address
===============

If the mail server tries to send a message to a nonexistent mailing list, it
will get a 550 error.

    >>> lmtp.sendmail(
    ...     'anne.person@example.com',
    ...     ['mylist@example.com'], """\
    ... From: anne.person@example.com
    ... To: mylist@example.com
    ... Subject: An interesting message
    ... Message-ID: <aardvark>
    ...
    ... This is an interesting message.
    ... """)
    Traceback (most recent call last):
    ...
    SMTPDataError: (550, 'Requested action not taken: mailbox unavailable')

Once the mailing list is created, the posting address is valid.
::

    >>> create_list('mylist@example.com')
    <mailing list "mylist@example.com" at ...>

    >>> transaction.commit()
    >>> lmtp.sendmail(
    ...     'anne.person@example.com',
    ...     ['mylist@example.com'], """\
    ... From: anne.person@example.com
    ... To: mylist@example.com
    ... Subject: An interesting message
    ... Message-ID: <badger>
    ...
    ... This is an interesting message.
    ... """)
    {}

Since the message itself is valid, it gets parsed and lands in the incoming
queue.

    >>> from mailman.testing.helpers import get_queue_messages
    >>> messages = get_queue_messages('in')
    >>> len(messages)
    1
    >>> print messages[0].msg.as_string()
    From: anne.person@example.com
    To: mylist@example.com
    Subject: An interesting message
    Message-ID: <badger>
    X-Message-ID-Hash: JYMZWSQ4IC2JPKK7ZUONRFRVC4ZYJGKJ
    X-MailFrom: anne.person@example.com
    <BLANKLINE>
    This is an interesting message.
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg    : False
    listname     : mylist@example.com
    original_size: ...
    to_list      : True
    version      : ...


Sub-addresses
=============

The LMTP server understands each of the list's sub-addreses, such as `-join`,
`-leave`, `-request` and so on.  If the message is posted to an invalid
sub-address though, it is rejected.

    >>> lmtp.sendmail(
    ...     'anne.person@example.com',
    ...     ['mylist-bogus@example.com'], """\
    ... From: anne.person@example.com
    ... To: mylist-bogus@example.com
    ... Subject: Help
    ... Message-ID: <cow>
    ...
    ... Please help me.
    ... """)
    Traceback (most recent call last):
    ...
    SMTPDataError: (550, 'Requested action not taken: mailbox unavailable')

But the message is accepted if posted to a valid sub-address.

    >>> lmtp.sendmail(
    ...     'anne.person@example.com',
    ...     ['mylist-request@example.com'], """\
    ... From: anne.person@example.com
    ... To: mylist-request@example.com
    ... Subject: Help
    ... Message-ID: <dog>
    ...
    ... Please help me.
    ... """)
    {}


Request subaddress
------------------

Depending on the subaddress, there is a message in the appropriate queue for
later processing.  For example, all `-request` messages are put into the
command queue for processing.

    >>> messages = get_queue_messages('command')
    >>> len(messages)
    1
    >>> print messages[0].msg.as_string()
    From: anne.person@example.com
    To: mylist-request@example.com
    Subject: Help
    Message-ID: <dog>
    X-Message-ID-Hash: 4SKREUSPI62BHDMFBSOZ3BMXFETSQHNA
    X-MailFrom: anne.person@example.com
    <BLANKLINE>
    Please help me.
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg    : False
    listname     : mylist@example.com
    original_size: ...
    subaddress   : request
    version      : ...


Bounce processor
----------------

A message to the `-bounces` address goes to the bounce processor.

    >>> lmtp.sendmail(
    ...     'mail-daemon@example.com',
    ...     ['mylist-bounces@example.com'], """\
    ... From: mail-daemon@example.com
    ... To: mylist-bounces@example.com
    ... Subject: A bounce
    ... Message-ID: <elephant>
    ...
    ... Bouncy bouncy.
    ... """)
    {}
    >>> messages = get_queue_messages('bounces')
    >>> len(messages)
    1
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg    : False
    listname     : mylist@example.com
    original_size: ...
    subaddress   : bounces
    version      : ...


Command processor
-----------------

Confirmation messages go to the command processor...

    >>> lmtp.sendmail(
    ...     'anne.person@example.com',
    ...     ['mylist-confirm@example.com'], """\
    ... From: anne.person@example.com
    ... To: mylist-confirm@example.com
    ... Subject: A bounce
    ... Message-ID: <falcon>
    ...
    ... confirm 123
    ... """)
    {}
    >>> messages = get_queue_messages('command')
    >>> len(messages)
    1
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg    : False
    listname     : mylist@example.com
    original_size: ...
    subaddress   : confirm
    version      : ...

...as do join messages...
::

    >>> lmtp.sendmail(
    ...     'anne.person@example.com',
    ...     ['mylist-join@example.com'], """\
    ... From: anne.person@example.com
    ... To: mylist-join@example.com
    ... Message-ID: <giraffe>
    ...
    ... """)
    {}
    >>> messages = get_queue_messages('command')
    >>> len(messages)
    1
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg    : False
    listname     : mylist@example.com
    original_size: ...
    subaddress   : join
    version      : ...

    >>> lmtp.sendmail(
    ...     'anne.person@example.com',
    ...     ['mylist-subscribe@example.com'], """\
    ... From: anne.person@example.com
    ... To: mylist-subscribe@example.com
    ... Message-ID: <hippopotamus>
    ...
    ... """)
    {}
    >>> messages = get_queue_messages('command')
    >>> len(messages)
    1
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg    : False
    listname     : mylist@example.com
    original_size: ...
    subaddress   : join
    version      : ...

...and leave messages.
::

    >>> lmtp.sendmail(
    ...     'anne.person@example.com',
    ...     ['mylist-leave@example.com'], """\
    ... From: anne.person@example.com
    ... To: mylist-leave@example.com
    ... Message-ID: <iguana>
    ...
    ... """)
    {}
    >>> messages = get_queue_messages('command')
    >>> len(messages)
    1
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg    : False
    listname     : mylist@example.com
    original_size: ...
    subaddress   : leave
    version      : ...

    >>> lmtp.sendmail(
    ...     'anne.person@example.com',
    ...     ['mylist-unsubscribe@example.com'], """\
    ... From: anne.person@example.com
    ... To: mylist-unsubscribe@example.com
    ... Message-ID: <jackal>
    ...
    ... """)
    {}
    >>> messages = get_queue_messages('command')
    >>> len(messages)
    1
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg    : False
    listname     : mylist@example.com
    original_size: ...
    subaddress   : leave
    version      : ...


Incoming processor
------------------

Messages to the `-owner` address also go to the incoming processor.

    >>> lmtp.sendmail(
    ...     'anne.person@example.com',
    ...     ['mylist-owner@example.com'], """\
    ... From: anne.person@example.com
    ... To: mylist-owner@example.com
    ... Message-ID: <kangaroo>
    ...
    ... """)
    {}
    >>> messages = get_queue_messages('in')
    >>> len(messages)
    1
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg    : False
    envsender    : noreply@example.com
    listname     : mylist@example.com
    original_size: ...
    subaddress   : owner
    to_owner     : True
    version      : ...


.. Clean up
   >>> master.stop()
