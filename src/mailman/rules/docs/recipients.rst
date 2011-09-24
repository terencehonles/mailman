============================
Maximum number of recipients
============================

This rule matches when there are more than the maximum allowed number of
explicit recipients addressed by the message.

    >>> mlist = create_list('_xtest@example.com')
    >>> rule = config.rules['max-recipients']
    >>> print rule.name
    max-recipients

In this case, we'll create a message with five recipients.  These include all
addresses in the ``To:`` and ``CC:`` headers.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: _xtest@example.com, bperson@example.com
    ... Cc: cperson@example.com
    ... Cc: dperson@example.com (Dan Person)
    ... To: Elly Q. Person <eperson@example.com>
    ...
    ... Hey folks!
    ... """)

For backward compatibility, the message must have fewer than the maximum
number of explicit recipients.

    >>> mlist.max_num_recipients = 5
    >>> rule.check(mlist, msg, {})
    True

    >>> mlist.max_num_recipients = 6
    >>> rule.check(mlist, msg, {})
    False

Zero means any number of recipients are allowed.

    >>> mlist.max_num_recipients = 0
    >>> rule.check(mlist, msg, {})
    False
