========
Messages
========

Mailman has its own Message classes, derived from the standard
``email.message.Message`` class, but providing additional useful methods.


User notifications
==================

When Mailman needs to send a message to a user, it creates a
``UserNotification`` instance, and then calls the ``.send()`` method on this
object.  This method requires a mailing list instance.

    >>> mlist = create_list('_xtest@example.com')

The ``UserNotification`` constructor takes the recipient address, the sender
address, an optional subject, optional body text, and optional language.

    >>> from mailman.email.message import UserNotification
    >>> msg = UserNotification(
    ...     'aperson@example.com',
    ...     '_xtest@example.com',
    ...     'Something you need to know',
    ...     'I needed to tell you this.')
    >>> msg.send(mlist)

The message will end up in the `virgin` queue.

    >>> switchboard = config.switchboards['virgin']
    >>> len(switchboard.files)
    1
    >>> filebase = switchboard.files[0]
    >>> qmsg, qmsgdata = switchboard.dequeue(filebase)
    >>> switchboard.finish(filebase)
    >>> print qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: Something you need to know
    From: _xtest@example.com
    To: aperson@example.com
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    I needed to tell you this.
