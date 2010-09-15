=================
No Subject header
=================

This rule matches if the message has no ``Subject:`` header, or if the header
is the empty string when stripped.

    >>> mlist = create_list('_xtest@example.com')
    >>> rule = config.rules['no-subject']
    >>> print rule.name
    no-subject

A message with a non-empty subject does not match the rule.

    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... To: _xtest@example.com
    ... Subject: A posted message
    ...
    ... """)
    >>> rule.check(mlist, msg, {})
    False

Delete the ``Subject:`` header and the rule matches.

    >>> del msg['subject']
    >>> rule.check(mlist, msg, {})
    True

Even a ``Subject:`` header with only whitespace still matches the rule.

    >>> msg['Subject'] = '    '
    >>> rule.check(mlist, msg, {})
    True
