===================
SMTP authentication
===================

The SMTP server may require authentication.  Mailman supports setting the SMTP
user name and password.  The actual authentication mechanism used is
determined by Python's `smtplib module`_, which tries the more secure
`CRAM-MD5` method first, followed by the less secure mechanisms `PLAIN` and
`LOGIN`.

When sending authentication data between Mailman and the MTA over an unsecured
network, the submission (mail) server should offer `CRAM-MD5` as mechanism to
have Python's `smtplib module` automatically choose the more secure mechanism.

When the user name and password match what's expected by the server,
everything is a-okay.

    >>> mlist = create_list('test@example.com')

By default there is no user name and password, but this matches what's
expected by the test server.

    >>> config.push('auth', """
    ... [mta]
    ... smtp_user: testuser
    ... smtp_pass: testpass
    ... """)

Attempting delivery first must authorize with the mail server.
::

    >>> from mailman.mta.bulk import BulkDelivery
    >>> bulk = BulkDelivery()

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: My first post
    ... Message-ID: <first>
    ...
    ... First post!
    ... """)

    >>> bulk.deliver(mlist, msg, dict(recipients=['bperson@example.com']))
    {}

    >>> print smtpd.get_authentication_credentials()
    PLAIN AHRlc3R1c2VyAHRlc3RwYXNz
    >>> config.pop('auth')

But if the user name and password does not match, the connection will fail.

    >>> config.push('auth', """
    ... [mta]
    ... smtp_user: baduser
    ... smtp_pass: badpass
    ... """)

    >>> bulk = BulkDelivery()
    >>> response = bulk.deliver(
    ...     mlist, msg, dict(recipients=['bperson@example.com']))
    >>> dump_msgdata(response)
    bperson@example.com: (571, 'Bad authentication')

    >>> config.pop('auth')


.. _`smtplib module`: http://docs.python.org/library/smtplib.html
