=============
Posting loops
=============

To avoid a posting loop, Mailman has a rule to check for the existence of an
RFC 2369 ``List-Post:`` header with the value of the list's posting address.

    >>> mlist = create_list('_xtest@example.com')
    >>> rule = config.rules['loop']
    >>> print rule.name
    loop

The header could be missing, in which case the rule does not match.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... An important message.
    ... """)
    >>> rule.check(mlist, msg, {})
    False

The header could be present, but not match the list's posting address.

    >>> msg['List-Post'] = 'not-this-list@example.com'
    >>> rule.check(mlist, msg, {})
    False

If the header is present and does match the posting address, the rule
matches.

    >>> del msg['list-post']
    >>> msg['List-Post'] = mlist.posting_address
    >>> rule.check(mlist, msg, {})
    True

Even if there are multiple ``List-Post:`` headers, as long as one with the
posting address exists, the rule matches.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... List-Post: not-this-list@example.com
    ... List-Post: _xtest@example.com
    ... List-Post: foo@example.com
    ...
    ... An important message.
    ... """)
    >>> rule.check(mlist, msg, {})
    True
