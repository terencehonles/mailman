=========
Emergency
=========

When the mailing list has its emergency flag set, all messages posted to the
list are held for moderator approval.

    >>> mlist = create_list('test@example.com')
    >>> rule = config.rules['emergency']
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: My first post
    ... Message-ID: <first>
    ...
    ... An important message.
    ... """)

By default, the mailing list does not have its emergency flag set.

    >>> mlist.emergency
    False
    >>> rule.check(mlist, msg, {})
    False

The emergency rule matches if the flag is set on the mailing list.

    >>> mlist.emergency = True
    >>> rule.check(mlist, msg, {})
    True

However, if the message metadata has a ``moderator_approved`` key set, then
even if the mailing list has its emergency flag set, the message still goes
through to the membership.

    >>> rule.check(mlist, msg, dict(moderator_approved=True))
    False
