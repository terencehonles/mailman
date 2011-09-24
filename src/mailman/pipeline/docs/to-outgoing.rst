====================
The outgoing handler
====================

Mailman's outgoing queue is used as the wrapper around SMTP delivery to the
upstream mail server.  The to-outgoing handler does little more than drop the
message into the outgoing queue.

    >>> mlist = create_list('test@example.com')

Craft a message destined for the outgoing queue.  Include some random metadata
as if this message had passed through some other handlers.
::

    >>> msg = message_from_string("""\
    ... Subject: Here is a message
    ...
    ... Something of great import.
    ... """)

    >>> msgdata = dict(foo=1, bar=2, verp=True)
    >>> handler = config.handlers['to-outgoing']
    >>> handler.process(mlist, msg, msgdata)

While the queued message will not be changed, the queued metadata will have an
additional key set: the mailing list name.

    >>> from mailman.testing.helpers import get_queue_messages
    >>> messages = get_queue_messages('out')
    >>> len(messages)
    1
    >>> print messages[0].msg.as_string()
    Subject: Here is a message
    <BLANKLINE>
    Something of great import.
    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg: False
    bar      : 2
    foo      : 1
    listname : test@example.com
    verp     : True
    version  : 3
