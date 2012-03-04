==================
The command runner
==================

This runner's purpose is to process and respond to email commands.  Commands
are extensible using the Mailman plug-in system, but Mailman comes with a
number of email commands out of the box.  These are processed when a message
is sent to the list's ``-request`` address.

    >>> mlist = create_list('test@example.com')
    >>> mlist.send_welcome_messages = False


A command in the Subject
========================

For example, the ``echo`` command simply echoes the original command back to
the sender.  The command can be in the ``Subject`` header.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test-request@example.com
    ... Subject: echo hello
    ... Message-ID: <aardvark>
    ...
    ... """)

    >>> from mailman.app.inject import inject_message
    >>> inject_message(mlist, msg, switchboard='command')
    >>> from mailman.runners.command import CommandRunner
    >>> from mailman.testing.helpers import make_testable_runner
    >>> command = make_testable_runner(CommandRunner)
    >>> command.run()

And now the response is in the ``virgin`` queue.
::

    >>> from mailman.testing.helpers import get_queue_messages
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> print messages[0].msg.as_string()
    Subject: The results of your email commands
    From: test-bounces@example.com
    To: aperson@example.com
    ...
    <BLANKLINE>
    The results of your email command are provided below.
    <BLANKLINE>
    - Original message details:
        From: aperson@example.com
        Subject: echo hello
        Date: ...
        Message-ID: <aardvark>
    <BLANKLINE>
    - Results:
    echo hello
    <BLANKLINE>
    - Done.
    <BLANKLINE>

    >>> dump_msgdata(messages[0].msgdata)
    _parsemsg           : False
    listname            : test@example.com
    nodecorate          : True
    recipients          : set([u'aperson@example.com'])
    reduced_list_headers: True
    version             : ...


A command in the body
=====================

The command can also be found in the body of the message, as long as the
message is plain text.
::

    >>> msg = message_from_string("""\
    ... From: bperson@example.com
    ... To: test-request@example.com
    ... Message-ID: <bobcat>
    ...
    ... echo foo bar
    ... """)

    >>> inject_message(mlist, msg, switchboard='command')
    >>> command.run()
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> print messages[0].msg.as_string()
    Subject: The results of your email commands
    From: test-bounces@example.com
    To: bperson@example.com
    ...
    Precedence: bulk
    <BLANKLINE>
    The results of your email command are provided below.
    <BLANKLINE>
    - Original message details:
        From: bperson@example.com
        Subject: n/a
        Date: ...
        Message-ID: <bobcat>
    <BLANKLINE>
    - Results:
    echo foo bar
    <BLANKLINE>
    - Done.
    <BLANKLINE>


Implicit commands
=================

For some commands, specifically for joining and leaving a mailing list, there
are email aliases that act like commands, even when there's nothing else in
the ``Subject`` or body.  For example, to join a mailing list, a user need
only email the ``-join`` address or ``-subscribe`` address (the latter is
deprecated).

Because Dirk has never registered with Mailman before, he gets two responses.
The first is a confirmation message so that Dirk can validate his email
address, and the other is the results of his email command.
::

    >>> msg = message_from_string("""\
    ... From: Dirk Person <dperson@example.com>
    ... To: test-join@example.com
    ...
    ... """)

    >>> inject_message(mlist, msg, switchboard='command', subaddress='join')
    >>> command.run()
    >>> messages = get_queue_messages('virgin', sort_on='subject')
    >>> len(messages)
    2

    >>> from mailman.interfaces.registrar import IRegistrar
    >>> from zope.component import getUtility
    >>> registrar = getUtility(IRegistrar)
    >>> for item in messages:
    ...     subject = item.msg['subject']
    ...     print 'Subject:', subject
    ...     if 'confirm' in str(subject):
    ...         token = str(subject).split()[1].strip()
    ...         status = registrar.confirm(token)
    ...         assert status, 'Confirmation failed'
    Subject: The results of your email commands
    Subject: confirm ...

.. Clear the queue
    >>> ignore = get_queue_messages('virgin')

Similarly, to leave a mailing list, the user need only email the ``-leave`` or
``-unsubscribe`` address (the latter is deprecated).
::

    >>> msg = message_from_string("""\
    ... From: dperson@example.com
    ... To: test-leave@example.com
    ...
    ... """)

    >>> inject_message(mlist, msg, switchboard='command', subaddress='leave')
    >>> command.run()
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> print messages[0].msg.as_string()
    Subject: The results of your email commands
    From: test-bounces@example.com
    To: dperson@example.com
    ...
    <BLANKLINE>
    The results of your email command are provided below.
    <BLANKLINE>
    - Original message details:
    From: dperson@example.com
    Subject: n/a
    Date: ...
    Message-ID: ...
    <BLANKLINE>
    - Results:
    Dirk Person <dperson@example.com> left test@example.com
    <BLANKLINE>
    - Done.
    <BLANKLINE>

The ``-confirm`` address is also available as an implicit command.
::

    >>> msg = message_from_string("""\
    ... From: dperson@example.com
    ... To: test-confirm+123@example.com
    ...
    ... """)

    >>> inject_message(mlist, msg, switchboard='command', subaddress='confirm')
    >>> command.run()
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> print messages[0].msg.as_string()
    Subject: The results of your email commands
    From: test-bounces@example.com
    To: dperson@example.com
    ...
    <BLANKLINE>
    The results of your email command are provided below.
    <BLANKLINE>
    - Original message details:
    From: dperson@example.com
    Subject: n/a
    Date: ...
    Message-ID: ...
    <BLANKLINE>
    - Results:
    Confirmation token did not match
    <BLANKLINE>
    - Done.
    <BLANKLINE>


Stopping command processing
===========================

The ``end`` command stops email processing, so that nothing following is
looked at by the command queue.
::

    >>> msg = message_from_string("""\
    ... From: cperson@example.com
    ... To: test-request@example.com
    ... Message-ID: <caribou>
    ...
    ... echo foo bar
    ... end ignored
    ... echo baz qux
    ... """)

    >>> inject_message(mlist, msg, switchboard='command')
    >>> command.run()
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> print messages[0].msg.as_string()
    Subject: The results of your email commands
    ...
    <BLANKLINE>
    - Results:
    echo foo bar
    <BLANKLINE>
    - Unprocessed:
    echo baz qux
    <BLANKLINE>
    - Done.
    <BLANKLINE>

The ``stop`` command is an alias for ``end``.
::

    >>> msg = message_from_string("""\
    ... From: cperson@example.com
    ... To: test-request@example.com
    ... Message-ID: <caribou>
    ...
    ... echo foo bar
    ... stop ignored
    ... echo baz qux
    ... """)

    >>> inject_message(mlist, msg, switchboard='command')
    >>> command.run()
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1

    >>> print messages[0].msg.as_string()
    Subject: The results of your email commands
    ...
    <BLANKLINE>
    - Results:
    echo foo bar
    <BLANKLINE>
    - Unprocessed:
    echo baz qux
    <BLANKLINE>
    - Done.
    <BLANKLINE>
