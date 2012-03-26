==========================
Automatic response handler
==========================

Mailman has a autoreply handler that sends automatic responses to messages it
receives on its posting address, owner address, or robot address.  Automatic
responses are subject to various conditions, such as headers in the original
message or the amount of time since the last auto-response.

    >>> mlist = create_list('_xtest@example.com')
    >>> mlist.display_name = 'XTest'


Basic automatic responding
==========================

Basic automatic responding occurs when the list is set up to respond to either
its ``-owner`` address, its ``-request`` address, or to the posting address,
and a message is sent to one of these addresses.  A mailing list also has an
automatic response grace period which specifies how much time must pass before
a second response will be sent, with 0 meaning "there is no grace period".
::

    >>> from datetime import timedelta
    >>> from mailman.interfaces.autorespond import ResponseAction

    >>> mlist.autorespond_owner = ResponseAction.respond_and_continue
    >>> mlist.autoresponse_grace_period = timedelta()
    >>> mlist.autoresponse_owner_text = 'owner autoresponse text'

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: _xtest-owner@example.com
    ...
    ... help
    ... """)

The preceding message to the mailing list's owner will trigger an automatic
response.
::

    >>> from mailman.testing.helpers import get_queue_messages

    >>> handler = config.handlers['replybot']
    >>> handler.process(mlist, msg, dict(to_owner=True))
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg           : False
    listname            : _xtest@example.com
    nodecorate          : True
    recipients          : set([u'aperson@example.com'])
    reduced_list_headers: True
    version             : 3

    >>> print messages[0].msg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: Auto-response for your message to the "XTest" mailing list
    From: _xtest-bounces@example.com
    To: aperson@example.com
    X-Mailer: The Mailman Replybot
    X-Ack: No
    Message-ID: <...>
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    owner autoresponse text


Short circuiting
================

Several headers in the original message determine whether an automatic
response should even be sent.  For example, if the message has an
``X-Ack: No`` header, no auto-response is sent.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... X-Ack: No
    ...
    ... help me
    ... """)

    >>> handler.process(mlist, msg, dict(to_owner=True))
    >>> get_queue_messages('virgin')
    []

Mailman itself can suppress automatic responses for certain types of
internally crafted messages, by setting the ``noack`` metadata key.
::

    >>> msg = message_from_string("""\
    ... From: mailman@example.com
    ...
    ... help for you
    ... """)

    >>> handler.process(mlist, msg, dict(noack=True, to_owner=True))
    >>> get_queue_messages('virgin')
    []

If there is a ``Precedence:`` header with any of the values ``bulk``,
``junk``, or ``list``, then the automatic response is also suppressed.
::

    >>> msg = message_from_string("""\
    ... From: asystem@example.com
    ... Precedence: bulk
    ...
    ... hey!
    ... """)

    >>> handler.process(mlist, msg, dict(to_owner=True))
    >>> get_queue_messages('virgin')
    []

    >>> msg.replace_header('precedence', 'junk')
    >>> handler.process(mlist, msg, dict(to_owner=True))
    >>> get_queue_messages('virgin')
    []

    >>> msg.replace_header('precedence', 'list')
    >>> handler.process(mlist, msg, dict(to_owner=True))
    >>> get_queue_messages('virgin')
    []

Unless the ``X-Ack:`` header has a value of ``yes``, in which case, the
``Precedence`` header is ignored.
::

    >>> msg['X-Ack'] = 'yes'
    >>> handler.process(mlist, msg, dict(to_owner=True))
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg           : False
    listname            : _xtest@example.com
    nodecorate          : True
    recipients          : set([u'asystem@example.com'])
    reduced_list_headers: True
    version             : 3

    >>> print messages[0].msg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: Auto-response for your message to the "XTest" mailing list
    From: _xtest-bounces@example.com
    To: asystem@example.com
    X-Mailer: The Mailman Replybot
    X-Ack: No
    Message-ID: <...>
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    owner autoresponse text


Available auto-responses
========================

As shown above, a message sent to the ``-owner`` address will get an
auto-response with the text set for owner responses.  Two other types of email
will get auto-responses: those sent to the ``-request`` address...
::

    >>> mlist.autorespond_requests = ResponseAction.respond_and_continue
    >>> mlist.autoresponse_request_text = 'robot autoresponse text'

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: _xtest-request@example.com
    ...
    ... help me
    ... """)

    >>> handler.process(mlist, msg, dict(to_request=True))
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> print messages[0].msg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: Auto-response for your message to the "XTest" mailing list
    From: _xtest-bounces@example.com
    To: aperson@example.com
    X-Mailer: The Mailman Replybot
    X-Ack: No
    Message-ID: <...>
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    robot autoresponse text

...and those sent to the posting address.
::

    >>> mlist.autorespond_postings = ResponseAction.respond_and_continue
    >>> mlist.autoresponse_postings_text = 'postings autoresponse text'

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: _xtest@example.com
    ...
    ... help me
    ... """)

    >>> handler.process(mlist, msg, dict(to_list=True))
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> print messages[0].msg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: Auto-response for your message to the "XTest" mailing list
    From: _xtest-bounces@example.com
    To: aperson@example.com
    X-Mailer: The Mailman Replybot
    X-Ack: No
    Message-ID: <...>
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    postings autoresponse text


Grace periods
=============

Automatic responses have a grace period, during which no additional responses
will be sent.  This is so as not to bombard the sender with responses.  The
grace period is measured in days.

    >>> mlist.autoresponse_grace_period = timedelta(days=10)

When a response is sent to a person via any of the owner, request, or postings
addresses, the response date is recorded.  The grace period is usually
measured in days.

    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ... To: _xtest-owner@example.com
    ...
    ... help
    ... """)

This is the first response to bperson, so it gets sent.

    >>> handler.process(mlist, msg, dict(to_owner=True))
    >>> print len(get_queue_messages('virgin'))
    1

But with a grace period greater than zero, no subsequent response will be sent
right now.

    >>> handler.process(mlist, msg, dict(to_owner=True))
    >>> print len(get_queue_messages('virgin'))
    0

Fast forward 9 days and you still don't get a response.
::

    >>> from mailman.utilities.datetime import factory
    >>> factory.fast_forward(days=9)

    >>> handler.process(mlist, msg, dict(to_owner=True))
    >>> print len(get_queue_messages('virgin'))
    0

But tomorrow, the sender will get a new auto-response.

    >>> factory.fast_forward()
    >>> handler.process(mlist, msg, dict(to_owner=True))
    >>> print len(get_queue_messages('virgin'))
    1

Of course, everything works the same way for messages to the request
address, even if the sender is the same person...
::

    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ... To: _xtest-request@example.com
    ...
    ... help
    ... """)

    >>> handler.process(mlist, msg, dict(to_request=True))
    >>> print len(get_queue_messages('virgin'))
    1

    >>> handler.process(mlist, msg, dict(to_request=True))
    >>> print len(get_queue_messages('virgin'))
    0

    >>> factory.fast_forward(days=9)
    >>> handler.process(mlist, msg, dict(to_request=True))
    >>> print len(get_queue_messages('virgin'))
    0

    >>> factory.fast_forward()
    >>> handler.process(mlist, msg, dict(to_request=True))
    >>> print len(get_queue_messages('virgin'))
    1

...and for messages to the posting address.
::

    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ... To: _xtest@example.com
    ...
    ... help
    ... """)

    >>> handler.process(mlist, msg, dict(to_list=True))
    >>> print len(get_queue_messages('virgin'))
    1

    >>> handler.process(mlist, msg, dict(to_list=True))
    >>> print len(get_queue_messages('virgin'))
    0

    >>> factory.fast_forward(days=9)
    >>> handler.process(mlist, msg, dict(to_list=True))
    >>> print len(get_queue_messages('virgin'))
    0

    >>> factory.fast_forward()
    >>> handler.process(mlist, msg, dict(to_list=True))
    >>> print len(get_queue_messages('virgin'))
    1
