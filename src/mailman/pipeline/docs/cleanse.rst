=================
Cleansing headers
=================

All messages posted to a list get their headers cleansed.  Some headers are
related to additional permissions that can be granted to the message and other
headers can be used to fish for membership.

    >>> mlist = create_list('_xtest@example.com')

Headers such as ``Approved``, ``Approve``, (as well as their ``X-`` variants)
and ``Urgent`` are used to grant special permissions to individual messages.
All may contain a password; the first two headers are used by list
administrators to pre-approve a message normal held for approval.  The latter
header is used to send a regular message to all members, regardless of whether
they get digests or not.  Because all three headers contain passwords, they
must be removed from any posted message.  ::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Approved: foobar
    ... Approve: barfoo
    ... X-Approved: bazbar
    ... X-Approve: barbaz
    ... Urgent: notreally
    ... Subject: A message of great import
    ...
    ... Blah blah blah
    ... """)

    >>> handler = config.handlers['cleanse']
    >>> handler.process(mlist, msg, {})
    >>> print msg.as_string()
    From: aperson@example.com
    Subject: A message of great import
    <BLANKLINE>
    Blah blah blah
    <BLANKLINE>

Other headers can be used by list members to fish the list for membership, so
we don't let them go through.  These are a mix of standard headers and custom
headers supported by some mail readers.  For example, ``X-PMRC`` is supported
by Pegasus mail.  I don't remember what program uses ``X-Confirm-Reading-To``
though (Some Microsoft product perhaps?).

    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ... Reply-To: bperson@example.org
    ... Sender: asystem@example.net
    ... Return-Receipt-To: another@example.com
    ... Disposition-Notification-To: athird@example.com
    ... X-Confirm-Reading-To: afourth@example.com
    ... X-PMRQC: afifth@example.com
    ... Subject: a message to you
    ...
    ... How are you doing?
    ... """)
    >>> handler.process(mlist, msg, {})
    >>> print msg.as_string()
    From: bperson@example.com
    Reply-To: bperson@example.org
    Sender: asystem@example.net
    Subject: a message to you
    <BLANKLINE>
    How are you doing?
    <BLANKLINE>


Anonymous lists
===============

Anonymous mailing lists also try to cleanse certain identifying headers from
the original posting, so that it is at least a bit more difficult to determine
who sent the message.  This isn't perfect though, for example, the body of the
messages are never scrubbed (though that might not be a bad idea).  The
``From`` and ``Reply-To`` headers in the posted message are taken from list
attributes.

Hotmail apparently sets ``X-Originating-Email``.

    >>> mlist.anonymous_list = True
    >>> mlist.description = 'A Test Mailing List'
    >>> mlist.preferred_language = 'en'
    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ... Reply-To: bperson@example.org
    ... Sender: asystem@example.net
    ... X-Originating-Email: cperson@example.com
    ... Subject: a message to you
    ...
    ... How are you doing?
    ... """)
    >>> handler.process(mlist, msg, {})
    >>> print msg.as_string()
    Subject: a message to you
    From: A Test Mailing List <_xtest@example.com>
    Reply-To: _xtest@example.com
    <BLANKLINE>
    How are you doing?
    <BLANKLINE>
