=======
Bounces
=======

When a message to an email address bounces, Mailman's bounce runner will
register a bounce event.  This registration is done through a utility.

    >>> from zope.component import getUtility
    >>> from zope.interface.verify import verifyObject
    >>> from mailman.interfaces.bounce import IBounceProcessor
    >>> processor = getUtility(IBounceProcessor)
    >>> verifyObject(IBounceProcessor, processor)
    True


Registration
============

When a bounce occurs, it's always within the context of a specific mailing
list.

    >>> mlist = create_list('test@example.com')

The bouncing email contains useful information that will be registered as
well.  In particular, the Message-ID is a key piece of data that needs to be
recorded.

    >>> msg = message_from_string("""\
    ... From: mail-daemon@example.org
    ... To: test-bounces@example.com
    ... Message-ID: <first>
    ...
    ... """)

There is a suite of bounce detectors that are used to heuristically extract
the bouncing email addresses.  Various techniques are employed including VERP,
DSN, and magic.  It is the bounce runner's responsibility to extract the set
of bouncing email addresses.  These are passed one-by-one to the registration
interface.

    >>> event = processor.register(mlist, 'anne@example.com', msg)
    >>> print event.list_name
    test@example.com
    >>> print event.email
    anne@example.com
    >>> print event.message_id
    <first>

Bounce events have a timestamp.

    >>> print event.timestamp
    2005-08-01 07:49:23

Bounce events have a flag indicating whether they've been processed or not.

    >>> event.processed
    False

When a bounce is registered, you can indicate the bounce context.

    >>> msg = message_from_string("""\
    ... From: mail-daemon@example.org
    ... To: test-bounces@example.com
    ... Message-ID: <second>
    ...
    ... """)

If no context is given, then a default one is used.

    >>> event = processor.register(mlist, 'bart@example.com', msg)
    >>> print event.message_id
    <second>
    >>> print event.context
    BounceContext.normal

A probe bounce carries more weight than just a normal bounce.

    >>> from mailman.interfaces.bounce import BounceContext
    >>> event = processor.register(
    ...     mlist, 'bart@example.com', msg, BounceContext.probe)
    >>> print event.message_id
    <second>
    >>> print event.context
    BounceContext.probe
