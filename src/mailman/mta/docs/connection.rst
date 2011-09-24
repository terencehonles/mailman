===============
MTA connections
===============

Outgoing connections to the outgoing mail transport agent (MTA) are mitigated
through a ``Connection`` class, which can transparently manage multiple
sessions in a single connection.

    >>> from mailman.mta.connection import Connection

The number of sessions per connections is specified when the ``Connection``
object is created, as is the host and port number of the SMTP server.  Zero
means there's an unlimited number of sessions per connection.

    >>> connection = Connection(
    ...     config.mta.smtp_host, int(config.mta.smtp_port), 0)

At the start, there have been no connections to the server.

    >>> smtpd.get_connection_count()
    0

By sending a message to the server, a connection is opened.
::

    >>> connection.sendmail('anne@example.com', ['bart@example.com'], """\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Subject: aardvarks
    ...
    ... """)
    {}

    >>> smtpd.get_connection_count()
    1

We can reset the connection count back to zero.
::

    >>> from smtplib import SMTP
    >>> def reset():
    ...     smtpd = SMTP()
    ...     smtpd.connect(config.mta.smtp_host, int(config.mta.smtp_port))
    ...     smtpd.docmd('RSET')

    >>> reset()
    >>> smtpd.get_connection_count()
    0

    >>> connection.quit()

By providing an SMTP user name and password in the configuration file, Mailman
will authenticate with the mail server after each new connection.
::

    >>> config.push('auth', """
    ... [mta]
    ... smtp_user: testuser
    ... smtp_pass: testpass
    ... """)

    >>> connection = Connection(
    ...     config.mta.smtp_host, int(config.mta.smtp_port), 0,
    ...     config.mta.smtp_user, config.mta.smtp_pass)
    >>> connection.sendmail('anne@example.com', ['bart@example.com'], """\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Subject: aardvarks
    ...
    ... """)
    {}
    >>> print smtpd.get_authentication_credentials()
    PLAIN AHRlc3R1c2VyAHRlc3RwYXNz

    >>> reset()
    >>> config.pop('auth')

However, a bad user name or password generates an error.

    >>> config.push('auth', """
    ... [mta]
    ... smtp_user: baduser
    ... smtp_pass: badpass
    ... """)

    >>> connection = Connection(
    ...     config.mta.smtp_host, int(config.mta.smtp_port), 0,
    ...     config.mta.smtp_user, config.mta.smtp_pass)
    >>> connection.sendmail('anne@example.com', ['bart@example.com'], """\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Subject: aardvarks
    ...
    ... """)
    Traceback (most recent call last):
    ...
    SMTPAuthenticationError: (571, 'Bad authentication')

    >>> reset()
    >>> config.pop('auth')


Sessions per connection
=======================

Let's say we specify a maximum number of sessions per connection of 2.  When
the third message is sent, the connection is torn down and a new one is
created.

The connection count starts at zero.
::

    >>> connection = Connection(
    ...     config.mta.smtp_host, int(config.mta.smtp_port), 2)

    >>> smtpd.get_connection_count()
    0

We send two messages through the ``Connection`` object.  Only one connection
is opened.
::

    >>> connection.sendmail('anne@example.com', ['bart@example.com'], """\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Subject: aardvarks
    ...
    ... """)
    {}

    >>> smtpd.get_connection_count()
    1

    >>> connection.sendmail('anne@example.com', ['bart@example.com'], """\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Subject: aardvarks
    ...
    ... """)
    {}

    >>> smtpd.get_connection_count()
    1

The third message would cause a third session, exceeding the maximum.  So the
current connection is closed and a new one opened.
::

    >>> connection.sendmail('anne@example.com', ['bart@example.com'], """\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Subject: aardvarks
    ...
    ... """)
    {}

    >>> smtpd.get_connection_count()
    2

A fourth message does not cause a new connection to be made.
::

    >>> connection.sendmail('anne@example.com', ['bart@example.com'], """\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Subject: aardvarks
    ...
    ... """)
    {}

    >>> smtpd.get_connection_count()
    2

But a fifth one does.
::

    >>> connection.sendmail('anne@example.com', ['bart@example.com'], """\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Subject: aardvarks
    ...
    ... """)
    {}

    >>> smtpd.get_connection_count()
    3


No maximum
==========

A value of zero means that there is an unlimited number of sessions per
connection.

    >>> connection = Connection(
    ...     config.mta.smtp_host, int(config.mta.smtp_port), 0)
    >>> reset()

Even after ten messages are sent, there's still been only one connection to
the server.
::

    >>> connection.debug = True
    >>> for i in range(10):
    ...     # Ignore the results.
    ...     results = connection.sendmail(
    ...         'anne@example.com', ['bart@example.com'], """\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Subject: aardvarks
    ...
    ... """)

    >>> smtpd.get_connection_count()
    1


Development mode
================

By putting Mailman into development mode, you can force the recipients to a
given hard-coded address.  This allows you to test Mailman without worrying
about accidental deliveries to unintended recipients.
::

    >>> config.push('devmode', """
    ... [devmode]
    ... enabled: yes
    ... recipient: zperson@example.com
    ... """)

    >>> smtpd.clear()
    >>> connection.sendmail(
    ...     'anne@example.com',
    ...     ['bart@example.com', 'cate@example.com'], """\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Subject: aardvarks
    ...
    ... """)
    {}

    >>> messages = list(smtpd.messages)
    >>> len(messages)
    1
    >>> print messages[0].as_string()
    From: anne@example.com
    To: bart@example.com
    Subject: aardvarks
    X-Peer: ...
    X-MailFrom: anne@example.com
    X-RcptTo: zperson@example.com, zperson@example.com
    <BLANKLINE>
    <BLANKLINE>

    >>> config.pop('devmode')
