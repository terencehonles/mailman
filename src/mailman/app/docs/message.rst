========
Messages
========

Mailman has its own `Message` classes, derived from the standard
``email.message.Message`` class, but providing additional useful methods.


User notifications
==================

When Mailman needs to send a message to a user, it creates a
``UserNotification`` instance, and then calls the ``.send()`` method on this
object.  This method requires a mailing list instance.

    >>> mlist = create_list('test@example.com')

The ``UserNotification`` constructor takes the recipient address, the sender
address, an optional subject, optional body text, and optional language.

    >>> from mailman.email.message import UserNotification
    >>> msg = UserNotification(
    ...     'aperson@example.com',
    ...     'test@example.com',
    ...     'Something you need to know',
    ...     'I needed to tell you this.')
    >>> msg.send(mlist)

The message will end up in the `virgin` queue.

    >>> from mailman.testing.helpers import get_queue_messages
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1
    >>> print messages[0].msg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: Something you need to know
    From: test@example.com
    To: aperson@example.com
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    I needed to tell you this.

The message above got a `Precedence: bulk` header added by default.  If the
message we're sending already has a `Precedence:` header, it shouldn't be
changed.

    >>> del msg['precedence']
    >>> msg['Precedence'] = 'list'
    >>> msg.send(mlist)

Again, the message will end up in the `virgin` queue but with the original
`Precedence:` header.

    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1
    >>> print messages[0].msg['precedence']
    list

Sometimes we want to send the message without a `Precedence:` header such as
when we send a probe message.

    >>> del msg['precedence']
    >>> msg.send(mlist, add_precedence=False)

Again, the message will end up in the `virgin` queue but without the
`Precedence:` header.

    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1
    >>> print messages[0].msg['precedence']
    None

However, if the message already has a `Precedence:` header, setting the
`precedence=False` argument will have no effect.

    >>> msg['Precedence'] = 'junk'
    >>> msg.send(mlist, add_precedence=False)
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1
    >>> print messages[0].msg['precedence']
    junk
