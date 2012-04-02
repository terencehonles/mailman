===============
The NNTP runner
===============

The NNTP runner gateways mailing list messages to an NNTP newsgroup.

    >>> mlist = create_list('test@example.com')
    >>> mlist.linked_newsgroup = 'comp.lang.python'

Get a handle on the NNTP server, which we'll use later to verify the posted
messages.

    >>> from mailman.testing.helpers import get_nntp_server
    >>> nntpd = get_nntp_server(cleanups)

A message gets posted to the mailing list.  It may contain some headers which
are prohibited by NNTP servers such as INN.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... NNTP-Posting-Host: news.example.com
    ... NNTP-Posting-Date: today
    ... X-Trace: blah blah
    ... X-Complaints-To: abuse@dom.ain
    ... Xref: blah blah
    ... Xref: blah blah
    ... Date-Received: yesterday
    ... Posted: tomorrow
    ... Posting-Version: 99.99
    ... Relay-Version: 88.88
    ... Received: blah blah
    ...
    ... A message
    ... """)

The message gets copied to the NNTP queue for preparation and posting.

    >>> filebase = config.switchboards['nntp'].enqueue(
    ...     msg, listname='test@example.com')
    >>> from mailman.testing.helpers import make_testable_runner
    >>> from mailman.runners.nntp import NNTPRunner
    >>> runner = make_testable_runner(NNTPRunner, 'nntp')
    >>> runner.run()

The message was successfully posted the NNTP server.

    >>> print nntpd.get_message().as_string()
    From: aperson@example.com
    To: test@example.com
    Newsgroups: comp.lang.python
    Message-ID: ...
    Lines: 1
    <BLANKLINE>
    A message
    <BLANKLINE>
