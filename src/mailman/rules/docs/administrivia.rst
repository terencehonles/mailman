=============
Administrivia
=============

The `administrivia` rule matches when the message contains some common email
commands in the ``Subject:`` header or first few lines of the payload.  This
is used to catch messages posted to the list which should have been sent to
the ``-request`` robot address.

    >>> mlist = create_list('_xtest@example.com')
    >>> mlist.administrivia = True
    >>> rule = config.rules['administrivia']
    >>> print rule.name
    administrivia

For example, if the ``Subject:`` header contains the word ``unsubscribe``, the
rule matches.

    >>> msg_1 = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: unsubscribe
    ...
    ... """)
    >>> rule.check(mlist, msg_1, {})
    True

Similarly, if the body of the message contains the word ``subscribe`` in the
first few lines of text, the rule matches.

    >>> msg_2 = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: I wish to join your list
    ...
    ... subscribe
    ... """)
    >>> rule.check(mlist, msg_2, {})
    True

In both cases, administrivia checking can be disabled.

    >>> mlist.administrivia = False
    >>> rule.check(mlist, msg_1, {})
    False
    >>> rule.check(mlist, msg_2, {})
    False

To make the administrivia heuristics a little more robust, the rule actually
looks for a minimum and maximum number of arguments, so that it really does
seem like a mis-addressed email command.  In this case, the ``confirm``
command requires at least one argument.  We don't give that here so the rule
will not match.

    >>> mlist.administrivia = True
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: confirm
    ...
    ... """)
    >>> rule.check(mlist, msg, {})
    False

But a real ``confirm`` message will match.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: confirm 12345
    ...
    ... """)
    >>> rule.check(mlist, msg, {})
    True

We don't show all the other possible email commands, but you get the idea.


Non-administrivia
=================

Of course, messages that don't contain administrivia, don't match the rule.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: examine
    ...
    ... persuade
    ... """)
    >>> rule.check(mlist, msg, {})
    False

Also, only ``text/plain`` parts are checked for administrivia, so any email
commands in other content type subparts are ignored.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... Subject: some administrivia
    ... Content-Type: text/x-special
    ...
    ... subscribe
    ... """)
    >>> rule.check(mlist, msg, {})
    False
