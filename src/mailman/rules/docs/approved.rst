=====================
Pre-approved postings
=====================

Messages can contain a pre-approval, which is used to bypass the normal
message approval queue.  This has several use cases:

  - A list administrator can send an emergency message to the mailing list
    from an unregistered address, for example if they are away from their
    normal email.

  - An automated script can be programmed to send a message to an otherwise
    moderated list.

In order to support this, a mailing list can be given a *moderator password*
which is shared among all the administrators.

    >>> mlist = create_list('test@example.com')

This password will not be stored in clear text, so it must be hashed using the
configured hash protocol.

    >>> from flufl.password import lookup, make_secret
    >>> scheme = lookup(config.passwords.password_scheme.upper())
    >>> mlist.moderator_password = make_secret('super secret', scheme)

The ``approved`` rule determines whether the message contains the proper
approval or not.

    >>> rule = config.rules['approved']
    >>> print rule.name
    approved


No approval
===========

The preferred header to check for approval is ``Approved:``.  If the message
does not have this header, the rule will not match.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... An important message.
    ... """)
    >>> rule.check(mlist, msg, {})
    False

If the rule has an ``Approved`` header, but the value of this header does not
match the moderator password, the rule will not match.  Note that the header
must contain the clear text version of the password.

    >>> msg['Approved'] = 'not the password'
    >>> rule.check(mlist, msg, {})
    False


The message is approved
=======================

By adding an ``Approved`` header with a matching password, the rule will
match.

    >>> del msg['approved']
    >>> msg['Approved'] = 'super secret'
    >>> rule.check(mlist, msg, {})
    True


Alternative headers
===================

Other headers can be used to stash the moderator password.  This rule also
checks the ``Approve`` header.

    >>> del msg['approved']
    >>> msg['Approve'] = 'super secret'
    >>> rule.check(mlist, msg, {})
    True

Similarly, an ``X-Approved`` header can be used.

    >>> del msg['approve']
    >>> msg['X-Approved'] = 'super secret'
    >>> rule.check(mlist, msg, {})
    True

And finally, an ``X-Approve`` header can be used.

    >>> del msg['x-approved']
    >>> msg['X-Approve'] = 'super secret'
    >>> rule.check(mlist, msg, {})
    True


Removal of header
=================

Technically, rules should not have side-effects, however this rule does remove
the ``Approved`` header (LP: #973790) when it matches.

    >>> del msg['x-approved']
    >>> msg['Approved'] = 'super secret'
    >>> rule.check(mlist, msg, {})
    True
    >>> print msg['approved']
    None

It also removes the header when it doesn't match.  If the rule didn't do this,
then the mailing list could be probed for its moderator password.

    >>> msg['Approved'] = 'not the password'
    >>> rule.check(mlist, msg, {})
    False
    >>> print msg['approved']
    None


Using a pseudo-header
=====================

Mail programs have varying degrees to which they support custom headers like
``Approved:``.  For this reason, Mailman also supports using a
*pseudo-header*, which is really just the first non-whitespace line in the
payload of the message.  If this pseudo-header looks like a matching
``Approved:`` header, the message is similarly allowed to pass.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... Approved: super secret
    ... An important message.
    ... """)
    >>> rule.check(mlist, msg, {})
    True

The pseudo-header is always removed from the body of plain text messages.

    >>> print msg.as_string()
    From: aperson@example.com
    Content-Transfer-Encoding: 7bit
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    <BLANKLINE>
    An important message.
    <BLANKLINE>

As before, a mismatch in the pseudo-header does not approve the message, but
the pseudo-header line is still removed.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... Approved: not the password
    ... An important message.
    ... """)
    >>> rule.check(mlist, msg, {})
    False

    >>> print msg.as_string()
    From: aperson@example.com
    Content-Transfer-Encoding: 7bit
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    <BLANKLINE>
    An important message.
    <BLANKLINE>


MIME multipart support
======================

Mailman searches for the pseudo-header as the first non-whitespace line in the
first ``text/plain`` message part of the message.  This allows the feature to
be used with MIME documents.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... MIME-Version: 1.0
    ... Content-Type: multipart/mixed; boundary="AAA"
    ...
    ... --AAA
    ... Content-Type: application/x-ignore
    ...
    ... Approved: not the password
    ... The above line will be ignored.
    ...
    ... --AAA
    ... Content-Type: text/plain
    ...
    ... Approved: super secret
    ... An important message.
    ... --AAA--
    ... """)
    >>> rule.check(mlist, msg, {})
    True

Like before, the pseudo-header is removed, but only from the text parts.

    >>> print msg.as_string()
    From: aperson@example.com
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="AAA"
    <BLANKLINE>
    --AAA
    Content-Type: application/x-ignore
    <BLANKLINE>
    Approved: not the password
    The above line will be ignored.
    <BLANKLINE>
    --AAA
    Content-Transfer-Encoding: 7bit
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    <BLANKLINE>
    An important message.
    --AAA--
    <BLANKLINE>

If the correct password is in the non-``text/plain`` part, it is ignored.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... MIME-Version: 1.0
    ... Content-Type: multipart/mixed; boundary="AAA"
    ...
    ... --AAA
    ... Content-Type: application/x-ignore
    ...
    ... Approved: super secret
    ... The above line will be ignored.
    ...
    ... --AAA
    ... Content-Type: text/plain
    ...
    ... Approved: not the password
    ... An important message.
    ... --AAA--
    ... """)
    >>> rule.check(mlist, msg, {})
    False

Pseudo-header is still stripped, but only from the ``text/plain`` part.

    >>> print msg.as_string()
    From: aperson@example.com
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="AAA"
    <BLANKLINE>
    --AAA
    Content-Type: application/x-ignore
    <BLANKLINE>
    Approved: super secret
    The above line will be ignored.
    <BLANKLINE>
    --AAA
    Content-Transfer-Encoding: 7bit
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    <BLANKLINE>
    An important message.
    --AAA--


Stripping text/html parts
=========================

Because some mail programs will include both a ``text/plain`` part and a
``text/html`` alternative, the rule must search the alternatives and strip
anything that looks like an ``Approved:`` header.

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... MIME-Version: 1.0
    ... Content-Type: multipart/mixed; boundary="AAA"
    ...
    ... --AAA
    ... Content-Type: text/html
    ...
    ... <html>
    ... <head></head>
    ... <body>
    ... <b>Approved: super secret</b>
    ... <p>The above line will be ignored.
    ... </body>
    ... </html>
    ...
    ... --AAA
    ... Content-Type: text/plain
    ...
    ... Approved: super secret
    ... An important message.
    ... --AAA--
    ... """)
    >>> rule.check(mlist, msg, {})
    True

And the header-like text in the ``text/html`` part was stripped.

    >>> print msg.as_string()
    From: aperson@example.com
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="AAA"
    <BLANKLINE>
    --AAA
    Content-Transfer-Encoding: 7bit
    MIME-Version: 1.0
    Content-Type: text/html; charset="us-ascii"
    <BLANKLINE>
    <html>
    <head></head>
    <body>
    <b></b>
    <p>The above line will be ignored.
    </body>
    </html>
    <BLANKLINE>
    --AAA
    Content-Transfer-Encoding: 7bit
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    <BLANKLINE>
    An important message.
    --AAA--
    <BLANKLINE>

This is true even if the rule does not match (i.e. the incorrect password was
given).
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... MIME-Version: 1.0
    ... Content-Type: multipart/mixed; boundary="AAA"
    ...
    ... --AAA
    ... Content-Type: text/html
    ...
    ... <html>
    ... <head></head>
    ... <body>
    ... <b>Approved: not the password</b>
    ... <p>The above line will be ignored.
    ... </body>
    ... </html>
    ...
    ... --AAA
    ... Content-Type: text/plain
    ...
    ... Approved: not the password
    ... An important message.
    ... --AAA--
    ... """)
    >>> rule.check(mlist, msg, {})
    False

    >>> print msg.as_string()
    From: aperson@example.com
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="AAA"
    <BLANKLINE>
    --AAA
    Content-Transfer-Encoding: 7bit
    MIME-Version: 1.0
    Content-Type: text/html; charset="us-ascii"
    <BLANKLINE>
    <html>
    <head></head>
    <body>
    <b></b>
    <p>The above line will be ignored.
    </body>
    </html>
    <BLANKLINE>
    --AAA
    Content-Transfer-Encoding: 7bit
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    <BLANKLINE>
    An important message.
    --AAA--
    <BLANKLINE>
