==============================
Command line message injection
==============================

You can inject a message directly into a queue directory via the command
line.
::

    >>> from mailman.commands.cli_inject import Inject
    >>> command = Inject()

    >>> class FakeArgs:
    ...     queue = None
    ...     show = False
    ...     filename = None
    ...     listname = None
    ...     keywords = []
    >>> args = FakeArgs()

    >>> class FakeParser:
    ...     def error(self, message):
    ...         print message
    >>> command.parser = FakeParser()

It's easy to find out which queues are available.
::

    >>> args.show = True
    >>> command.process(args)
    Available queues:
        archive
        bad
        bounces
        command
        digest
        in
        lmtp
        nntp
        out
        pipeline
        rest
        retry
        shunt
        virgin

    >>> args.show = False

Usually, the text of the message to inject is in a file.

    >>> import os, tempfile
    >>> fd, filename = tempfile.mkstemp()
    >>> with os.fdopen(fd, 'w') as fp:
    ...     print >> fp, """\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: testing
    ... Message-ID: <aardvark>
    ...
    ... This is a test message.
    ... """

However, the mailing list name is always required.

    >>> args.filename = filename
    >>> command.process(args)
    List name is required

Let's provide a list name and try again.
::

    >>> mlist = create_list('test@example.com')
    >>> transaction.commit()
    >>> from mailman.testing.helpers import get_queue_messages

    >>> get_queue_messages('in')
    []
    >>> args.listname = ['test@example.com']
    >>> command.process(args)

By default, the incoming queue is used.
::

    >>> items = get_queue_messages('in')
    >>> len(items)
    1
    >>> print items[0].msg.as_string()
    From: aperson@example.com
    To: test@example.com
    Subject: testing
    Message-ID: ...
    Date: ...
    <BLANKLINE>
    This is a test message.
    <BLANKLINE>
    <BLANKLINE>

    >>> dump_msgdata(items[0].msgdata)
    _parsemsg    : False
    listname     : test@example.com
    original_size: 203
    version      : 3

But a different queue can be specified on the command line.
::

    >>> args.queue = 'virgin'
    >>> command.process(args)

    >>> get_queue_messages('in')
    []
    >>> items = get_queue_messages('virgin')
    >>> len(items)
    1
    >>> print items[0].msg.as_string()
    From: aperson@example.com
    To: test@example.com
    Subject: testing
    Message-ID: ...
    Date: ...
    <BLANKLINE>
    This is a test message.
    <BLANKLINE>
    <BLANKLINE>

    >>> dump_msgdata(items[0].msgdata)
    _parsemsg    : False
    listname     : test@example.com
    original_size: 203
    version      : 3


Standard input
==============

The message text can also be provided on standard input.
::

    >>> from StringIO import StringIO

    # Remember: we've got unicode literals turned on.
    >>> standard_in = StringIO(str("""\
    ... From: bperson@example.com
    ... To: test@example.com
    ... Subject: another test
    ... Message-ID: <badger>
    ...
    ... This is another test message.
    ... """))

    >>> import sys
    >>> sys.stdin = standard_in
    >>> args.filename = '-'
    >>> args.queue = None

    >>> command.process(args)
    >>> items = get_queue_messages('in')
    >>> len(items)
    1
    >>> print items[0].msg.as_string()
    From: bperson@example.com
    To: test@example.com
    Subject: another test
    Message-ID: ...
    Date: ...
    <BLANKLINE>
    This is another test message.
    <BLANKLINE>
    <BLANKLINE>

    >>> dump_msgdata(items[0].msgdata)
    _parsemsg    : False
    listname     : test@example.com
    original_size: 211
    version      : 3

.. Clean up.
   >>> sys.stdin = sys.__stdin__
   >>> args.filename = filename


Metadata
========

Additional metadata keys can be provided on the command line.  These key/value
pairs get added to the message metadata dictionary when the message is
injected.
::

    >>> args = FakeArgs()
    >>> args.filename = filename
    >>> args.listname = ['test@example.com']
    >>> args.keywords = ['foo=one', 'bar=two']
    >>> command.process(args)

    >>> items = get_queue_messages('in')
    >>> dump_msgdata(items[0].msgdata)
    _parsemsg    : False
    bar          : two
    foo          : one
    listname     : test@example.com
    original_size: 203
    version      : 3


Errors
======

It is an error to specify a queue that doesn't exist.

    >>> args.queue = 'xxbogusxx'
    >>> command.process(args)
    No such queue: xxbogusxx

It is also an error to specify a mailing list that doesn't exist.

    >>> args.queue = None
    >>> args.listname = ['bogus']
    >>> command.process(args)
    No such list: bogus


..
    # Clean up the tempfile.
    >>> os.remove(filename)
