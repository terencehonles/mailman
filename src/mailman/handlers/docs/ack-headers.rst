======================
Acknowledgment headers
======================

Messages that flow through the global pipeline get their headers `cooked`,
which basically means that their headers go through several mostly unrelated
transformations.  Some headers get added, others get changed.  Some of these
changes depend on mailing list settings and others depend on how the message
is getting sent through the system.  We'll take things one-by-one.

    >>> mlist = create_list('_xtest@example.com')
    >>> mlist.subject_prefix = ''

When the message's metadata has a `noack` key set, an ``X-Ack: no`` header is
added.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... A message of great import.
    ... """)

    >>> from mailman.handlers.cook_headers import process
    >>> process(mlist, msg, dict(noack=True))
    >>> print msg.as_string()
    From: aperson@example.com
    X-Ack: no
    ...

Any existing ``X-Ack`` header in the original message is removed.

    >>> msg = message_from_string("""\
    ... X-Ack: yes
    ... From: aperson@example.com
    ...
    ... A message of great import.
    ... """)
    >>> process(mlist, msg, dict(noack=True))
    >>> print msg.as_string()
    From: aperson@example.com
    X-Ack: no
    ...
