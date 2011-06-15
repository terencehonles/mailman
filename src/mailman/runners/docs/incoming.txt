===================
The incoming runner
===================

This runner's sole purpose in life is to decide the disposition of the
message.  It can either be accepted for delivery, rejected (i.e. bounced),
held for moderator approval, or discarded.

The runner operates by processing chains on a message/metadata pair in the
context of a mailing list.  Each mailing list may have a 'start chain' where
processing begins, with a global default.  This chain is processed with the
message eventually ending up in one of the four disposition states described
above.

    >>> mlist = create_list('test@example.com')
    >>> print mlist.start_chain
    built-in


Sender addresses
================

The incoming runner ensures that the sender addresses on the message are
registered with the system.  This is used for determining nonmember posting
privileges.  The addresses will not be linked to a user and will be
unverified, so if the real user comes along later and claims the address, it
will be linked to their user account (and must be verified).

While configurable, the *sender addresses* by default are those named in the
`From:`, `Sender:`, and `Reply-To:` headers, as well as the envelope sender
(though we won't worry about the latter).
::

    >>> msg = message_from_string("""\
    ... From: zperson@example.com
    ... Reply-To: yperson@example.com
    ... Sender: xperson@example.com
    ... To: test@example.com
    ... Subject: This is spiced ham
    ... Message-ID: <bogus>
    ...
    ... """)

    >>> from zope.component import getUtility
    >>> from mailman.interfaces.usermanager import IUserManager
    >>> user_manager = getUtility(IUserManager)
    >>> print user_manager.get_address('xperson@example.com')
    None
    >>> print user_manager.get_address('yperson@example.com')
    None
    >>> print user_manager.get_address('zperson@example.com')
    None

Inject the message into the incoming queue, similar to the way the upstream
mail server normally would.

    >>> from mailman.app.inject import inject_message
    >>> inject_message(mlist, msg)

The incoming runner runs until it is empty.

    >>> from mailman.runners.incoming import IncomingRunner
    >>> from mailman.testing.helpers import make_testable_runner
    >>> incoming = make_testable_runner(IncomingRunner, 'in')
    >>> incoming.run()

And now the addresses are known to the system.  As mentioned above, they are
not linked to a user and are unverified.

    >>> for localpart in ('xperson', 'yperson', 'zperson'):
    ...     email = '{0}@example.com'.format(localpart)
    ...     address = user_manager.get_address(email)
    ...     print '{0}; verified? {1}; user? {2}'.format(
    ...         address.email,
    ...         ('No' if address.verified_on is None else 'Yes'),
    ...         user_manager.get_user(email))
    xperson@example.com; verified? No; user? None
    yperson@example.com; verified? No; user? None
    zperson@example.com; verified? No; user? None

..
    Clear the pipeline queue of artifacts that affect the following tests.
    >>> from mailman.testing.helpers import get_queue_messages
    >>> ignore = get_queue_messages('pipeline')


Accepted messages
=================

We have a message that is going to be sent to the mailing list.  Once Anne is
a member of the mailing list, this message is so perfectly fine for posting
that it will be accepted and forward to the pipeline queue.

    >>> from mailman.testing.helpers import subscribe
    >>> subscribe(mlist, 'Anne')
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: My first post
    ... Message-ID: <first>
    ...
    ... First post!
    ... """)

Inject the message into the incoming queue and run until the queue is empty.

    >>> inject_message(mlist, msg)
    >>> incoming.run()

Now the message is in the pipeline queue.

    >>> pipeline_queue = config.switchboards['pipeline']
    >>> len(pipeline_queue.files)
    1
    >>> incoming_queue = config.switchboards['in']
    >>> len(incoming_queue.files)
    0
    >>> item = get_queue_messages('pipeline')[0]
    >>> print item.msg.as_string()
    From: aperson@example.com
    To: test@example.com
    Subject: My first post
    Message-ID: <first>
    Date: ...
    X-Mailman-Rule-Misses: approved; emergency; loop; member-moderation;
        administrivia; implicit-dest; max-recipients; max-size;
        news-moderation; no-subject; suspicious-header; nonmember-moderation
    <BLANKLINE>
    First post!
    <BLANKLINE>
    >>> dump_msgdata(item.msgdata)
    _parsemsg    : False
    envsender    : noreply@example.com
    ...


Held messages
=============

The list moderator sets the emergency flag on the mailing list.  The built-in
chain will now hold all posted messages, so nothing will show up in the
pipeline queue.
::

    >>> from mailman.chains.base import ChainNotification
    >>> def on_chain(event):
    ...     if isinstance(event, ChainNotification):
    ...         print event
    ...         print event.chain
    ...         print 'From: {0}\nTo: {1}\nMessage-ID: {2}'.format(
    ...             event.msg['from'], event.msg['to'],
    ...             event.msg['message-id'])

    >>> mlist.emergency = True

    >>> from mailman.testing.helpers import event_subscribers
    >>> with event_subscribers(on_chain):
    ...     inject_message(mlist, msg)
    ...     incoming.run()
    <mailman.chains.hold.HoldNotification ...>
    <mailman.chains.hold.HoldChain ...>
    From: aperson@example.com
    To: test@example.com
    Message-ID: <first>

    >>> mlist.emergency = False


Discarded messages
==================

Another possibility is that the message would get immediately discarded.  The
built-in chain does not have such a disposition by default, so let's craft a
new chain and set it as the mailing list's start chain.
::

    >>> from mailman.chains.base import Chain, Link
    >>> from mailman.interfaces.chain import LinkAction
    >>> def make_chain(name, target_chain):
    ...     truth_rule = config.rules['truth']
    ...     target_chain = config.chains[target_chain]
    ...     test_chain = Chain(name, 'Testing {0}'.format(target_chain))
    ...     config.chains[test_chain.name] = test_chain
    ...     link = Link(truth_rule, LinkAction.jump, target_chain)
    ...     test_chain.append_link(link)
    ...     return test_chain

    >>> test_chain = make_chain('always-discard', 'discard')
    >>> mlist.start_chain = test_chain.name

    >>> msg.replace_header('message-id', '<second>')
    >>> with event_subscribers(on_chain):
    ...     inject_message(mlist, msg)
    ...     incoming.run()
    <mailman.chains.discard.DiscardNotification ...>
    <mailman.chains.discard.DiscardChain ...>
    From: aperson@example.com
    To: test@example.com
    Message-ID: <second>

    >>> del config.chains[test_chain.name]

..
    The virgin queue needs to be cleared out due to artifacts from the
    previous tests above.

    >>> virgin_queue = config.switchboards['virgin']
    >>> ignore = get_queue_messages('virgin')


Rejected messages
=================

Similar to discarded messages, a message can be rejected, or bounced back to
the original sender.  Again, the built-in chain doesn't support this so we'll
just create a new chain that does.

    >>> test_chain = make_chain('always-reject', 'reject')
    >>> mlist.start_chain = test_chain.name

    >>> msg.replace_header('message-id', '<third>')
    >>> with event_subscribers(on_chain):
    ...     inject_message(mlist, msg)
    ...     incoming.run()
    <mailman.chains.reject.RejectNotification ...>
    <mailman.chains.reject.RejectChain ...>
    From: aperson@example.com
    To: test@example.com
    Message-ID: <third>

The rejection message is sitting in the virgin queue waiting to be delivered
to the original sender.

    >>> len(virgin_queue.files)
    1
    >>> item = get_queue_messages('virgin')[0]
    >>> print item.msg.as_string()
    Subject: My first post
    From: test-owner@example.com
    To: aperson@example.com
    ...
    <BLANKLINE>
    --===============...
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    <BLANKLINE>
    [No bounce details are available]
    --===============...
    Content-Type: message/rfc822
    MIME-Version: 1.0
    <BLANKLINE>
    From: aperson@example.com
    To: test@example.com
    Subject: My first post
    Message-ID: <third>
    Date: ...
    <BLANKLINE>
    First post!
    <BLANKLINE>
    --===============...

    >>> del config.chains['always-reject']
