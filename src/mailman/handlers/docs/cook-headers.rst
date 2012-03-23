===============
Cooking headers
===============

Messages that flow through the global pipeline get their headers 'cooked',
which basically means that their headers go through several mostly unrelated
transformations.  Some headers get added, others get changed.  Some of these
changes depend on mailing list settings and others depend on how the message
is getting sent through the system.  We'll take things one-by-one.

    >>> mlist = create_list('test@example.com')
    >>> mlist.subject_prefix = ''


Saving the original sender
==========================

Because the original sender headers may get deleted or changed, this handler
will place the sender in the message metadata for safe keeping.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... A message of great import.
    ... """)
    >>> msgdata = {}

    >>> from mailman.handlers.cook_headers import process
    >>> process(mlist, msg, msgdata)
    >>> print msgdata['original_sender']
    aperson@example.com

But if there was no original sender, then the empty string will be saved.

    >>> msg = message_from_string("""\
    ... Subject: No original sender
    ...
    ... A message of great import.
    ... """)
    >>> msgdata = {}
    >>> process(mlist, msg, msgdata)
    >>> print msgdata['original_sender']
    <BLANKLINE>


Mailman version header
======================

Mailman will also insert an ``X-Mailman-Version`` header...

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... A message of great import.
    ... """)
    >>> process(mlist, msg, {})
    >>> from mailman.version import VERSION
    >>> msg['x-mailman-version'] == VERSION
    True

...but only if one doesn't already exist.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... X-Mailman-Version: 3000
    ...
    ... A message of great import.
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['x-mailman-version']
    3000


Precedence header
=================

Mailman will insert a ``Precedence`` header, which is a de-facto standard for
telling automatic reply software (e.g. ``vacation(1)``) not to respond to this
message.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... A message of great import.
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['precedence']
    list

But Mailman will only add that header if the original message doesn't already
have one of them.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Precedence: junk
    ...
    ... A message of great import.
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg['precedence']
    junk


Personalization
===============

The ``To`` field normally contains the list posting address.  However when
messages are fully personalized, that header will get overwritten with the
address of the recipient.  The list's posting address will be added to one of
the recipient headers so that users will be able to reply back to the list.

    >>> from mailman.interfaces.mailinglist import (
    ...     Personalization, ReplyToMunging)
    >>> mlist.personalize = Personalization.full
    >>> mlist.reply_goes_to_list = ReplyToMunging.no_munging
    >>> mlist.description = 'My test mailing list'
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... """)
    >>> process(mlist, msg, {})
    >>> print msg.as_string()
    From: aperson@example.com
    X-Mailman-Version: ...
    Precedence: list
    Cc: My test mailing list <test@example.com>
    <BLANKLINE>
    <BLANKLINE>
