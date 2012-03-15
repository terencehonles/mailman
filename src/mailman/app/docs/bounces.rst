=======
Bounces
=======

An important feature of Mailman is automatic bounce process.


Bounces, or message rejection
=============================

Mailman can bounce messages back to the original sender.  This is essentially
equivalent to rejecting the message with notification.  Mailing lists can
bounce a message with an optional error message.

    >>> mlist = create_list('text@example.com')

Any message can be bounced.

    >>> msg = message_from_string("""\
    ... To: text@example.com
    ... From: aperson@example.com
    ... Subject: Something important
    ...
    ... I sometimes say something important.
    ... """)

Bounce a message by passing in the original message, and an optional error
message.  The bounced message ends up in the virgin queue, awaiting sending
to the original message author.

    >>> from mailman.app.bounces import bounce_message
    >>> bounce_message(mlist, msg)
    >>> from mailman.testing.helpers import get_queue_messages
    >>> items = get_queue_messages('virgin')
    >>> len(items)
    1
    >>> print items[0].msg.as_string()
    Subject: Something important
    From: text-owner@example.com
    To: aperson@example.com
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="..."
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    --...
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    <BLANKLINE>
    [No bounce details are available]
    --...
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    To: text@example.com
    From: aperson@example.com
    Subject: Something important
    <BLANKLINE>
    I sometimes say something important.
    <BLANKLINE>
    --...--

An error message can be given when the message is bounced, and this will be
included in the payload of the text/plain part.  The error message must be
passed in as an instance of a ``RejectMessage`` exception.

    >>> from mailman.core.errors import RejectMessage
    >>> error = RejectMessage("This wasn't very important after all.")
    >>> bounce_message(mlist, msg, error)
    >>> items = get_queue_messages('virgin')
    >>> len(items)
    1
    >>> print items[0].msg.as_string()
    Subject: Something important
    From: text-owner@example.com
    To: aperson@example.com
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="..."
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    --...
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    <BLANKLINE>
    This wasn't very important after all.
    --...
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    To: text@example.com
    From: aperson@example.com
    Subject: Something important
    <BLANKLINE>
    I sometimes say something important.
    <BLANKLINE>
    --...--
