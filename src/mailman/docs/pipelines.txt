=========
Pipelines
=========

This runner's purpose in life is to process messages that have been accepted
for posting, applying any modifications and also sending copies of the message
to the archives, digests, nntp, and outgoing queues.  Pipelines are named and
consist of a sequence of handlers, each of which is applied in turn.  Unlike
rules and chains, there is no way to stop a pipeline from processing the
message once it's started.

    >>> mlist = create_list('xtest@example.com')
    >>> print mlist.pipeline
    built-in
    >>> from mailman.core.pipelines import process


Processing a message
====================

Messages hit the pipeline after they've been accepted for posting.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: xtest@example.com
    ... Subject: My first post
    ... Message-ID: <first>
    ...
    ... First post!
    ... """)
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata, mlist.pipeline)

The message has been modified with additional headers, footer decorations,
etc.

    >>> print msg.as_string()
    From: aperson@example.com
    To: xtest@example.com
    Message-ID: <first>
    Subject: [Xtest] My first post
    X-BeenThere: xtest@example.com
    X-Mailman-Version: ...
    Precedence: list
    List-Id: <xtest.example.com>
    X-Message-ID-Hash: 4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB
    List-Post: <mailto:xtest@example.com>
    List-Subscribe:
        <http://lists.example.com/listinfo/xtest@example.com>,
        <mailto:xtest-join@example.com>
    Archived-At:
        http://lists.example.com/archives/4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB
    List-Unsubscribe:
        <http://lists.example.com/listinfo/xtest@example.com>,
        <mailto:xtest-leave@example.com>
    List-Archive: <http://lists.example.com/archives/xtest@example.com>
    List-Help: <mailto:xtest-request@example.com?subject=help>
    <BLANKLINE>
    First post!
    <BLANKLINE>

And the message metadata has information about recipients and other stuff.
However there are currently no recipients for this message.

    >>> dump_msgdata(msgdata)
    original_sender : aperson@example.com
    origsubj        : My first post
    recipients      : set([])
    stripped_subject: My first post

And the message is now sitting in various other processing queues.

    >>> from mailman.testing.helpers import get_queue_messages
    >>> messages = get_queue_messages('archive')
    >>> len(messages)
    1
    >>> print messages[0].msg.as_string()
    From: aperson@example.com
    To: xtest@example.com
    Message-ID: <first>
    Subject: [Xtest] My first post
    X-BeenThere: xtest@example.com
    X-Mailman-Version: ...
    Precedence: list
    List-Id: <xtest.example.com>
    X-Message-ID-Hash: 4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB
    List-Post: <mailto:xtest@example.com>
    List-Subscribe:
        <http://lists.example.com/listinfo/xtest@example.com>,
        <mailto:xtest-join@example.com>
    Archived-At:
        http://lists.example.com/archives/4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB
    List-Unsubscribe:
        <http://lists.example.com/listinfo/xtest@example.com>,
        <mailto:xtest-leave@example.com>
    List-Archive: <http://lists.example.com/archives/xtest@example.com>
    List-Help: <mailto:xtest-request@example.com?subject=help>
    <BLANKLINE>
    First post!
    <BLANKLINE>
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg       : False
    original_sender : aperson@example.com
    origsubj        : My first post
    recipients      : set([])
    stripped_subject: My first post
    version         : 3

This mailing list is not linked to an NNTP newsgroup, so there's nothing in
the outgoing nntp queue.

    >>> messages = get_queue_messages('news')
    >>> len(messages)
    0

This is the message that will actually get delivered to end recipients.

    >>> messages = get_queue_messages('out')
    >>> len(messages)
    1
    >>> print messages[0].msg.as_string()
    From: aperson@example.com
    To: xtest@example.com
    Message-ID: <first>
    Subject: [Xtest] My first post
    X-BeenThere: xtest@example.com
    X-Mailman-Version: ...
    Precedence: list
    List-Id: <xtest.example.com>
    X-Message-ID-Hash: 4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB
    List-Post: <mailto:xtest@example.com>
    List-Subscribe:
        <http://lists.example.com/listinfo/xtest@example.com>,
        <mailto:xtest-join@example.com>
    Archived-At:
        http://lists.example.com/archives/4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB
    List-Unsubscribe:
        <http://lists.example.com/listinfo/xtest@example.com>,
        <mailto:xtest-leave@example.com>
    List-Archive: <http://lists.example.com/archives/xtest@example.com>
    List-Help: <mailto:xtest-request@example.com?subject=help>
    <BLANKLINE>
    First post!
    <BLANKLINE>
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg       : False
    listname        : xtest@example.com
    original_sender : aperson@example.com
    origsubj        : My first post
    recipients      : set([])
    stripped_subject: My first post
    version         : 3

There's now one message in the digest mailbox, getting ready to be sent.

    >>> from mailman.testing.helpers import digest_mbox
    >>> digest = digest_mbox(mlist)
    >>> sum(1 for mboxmsg in digest)
    1
    >>> print list(digest)[0].as_string()
    From: aperson@example.com
    To: xtest@example.com
    Message-ID: <first>
    Subject: [Xtest] My first post
    X-BeenThere: xtest@example.com
    X-Mailman-Version: ...
    Precedence: list
    List-Id: <xtest.example.com>
    X-Message-ID-Hash: 4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB
    List-Post: <mailto:xtest@example.com>
    List-Subscribe:
        <http://lists.example.com/listinfo/xtest@example.com>,
        <mailto:xtest-join@example.com>
    Archived-At:
        http://lists.example.com/archives/4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB
    List-Unsubscribe:
        <http://lists.example.com/listinfo/xtest@example.com>,
        <mailto:xtest-leave@example.com>
    List-Archive: <http://lists.example.com/archives/xtest@example.com>
    List-Help: <mailto:xtest-request@example.com?subject=help>
    <BLANKLINE>
    First post!
    <BLANKLINE>
    <BLANKLINE>


Clean up the digests
====================

    >>> digest.clear()
    >>> digest.flush()
    >>> sum(1 for msg in digest_mbox(mlist))
    0
