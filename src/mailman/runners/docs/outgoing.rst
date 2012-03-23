===============
Outgoing runner
===============

The outgoing runner is the process that delivers messages to the directly
upstream SMTP server.  It is this upstream SMTP server that performs final
delivery to the intended recipients.

Messages that appear in the outgoing queue are processed individually through
a *delivery module*, essentially a pluggable interface for determining how the
recipient set will be batched, whether messages will be personalized and
VERP'd, etc.  The outgoing runner doesn't itself support retrying but it can
move messages to the 'retry queue' for handling delivery failures.
::

    >>> mlist = create_list('test@example.com')

    >>> from mailman.app.membership import add_member
    >>> from mailman.interfaces.member import DeliveryMode
    >>> add_member(mlist, 'aperson@example.com', 'Anne Person',
    ...            'password', DeliveryMode.regular, 'en')
    <Member: Anne Person <aperson@example.com>
             on test@example.com as MemberRole.member>
    >>> add_member(mlist, 'bperson@example.com', 'Bart Person',
    ...            'password', DeliveryMode.regular, 'en')
    <Member: Bart Person <bperson@example.com>
             on test@example.com as MemberRole.member>
    >>> add_member(mlist, 'cperson@example.com', 'Cris Person',
    ...            'password', DeliveryMode.regular, 'en')
    <Member: Cris Person <cperson@example.com>
             on test@example.com as MemberRole.member>

Normally, messages would show up in the outgoing queue after the message has
been processed by the rule set and pipeline.  But we can simulate that here by
injecting a message directly into the outgoing queue.  First though, we must
call the ``member-recipients`` handler so that the message metadata will be
populated with the list of addresses to deliver the message to.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ... To: test@example.com
    ... Subject: My first post
    ... Message-ID: <first>
    ...
    ... First post!
    ... """)

    >>> msgdata = {}
    >>> handler = config.handlers['member-recipients']
    >>> handler.process(mlist, msg, msgdata)
    >>> outgoing_queue = config.switchboards['out']

The ``to-outgoing`` handler populates the message metadata with the
destination mailing list name.  Simulate that here too.

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     tolist=True,
    ...     listname=mlist.fqdn_listname)

Running the outgoing runner processes the message, delivering it to the
upstream SMTP.

    >>> from mailman.runners.outgoing import OutgoingRunner
    >>> from mailman.testing.helpers import make_testable_runner
    >>> outgoing = make_testable_runner(OutgoingRunner, 'out')
    >>> outgoing.run()

Every recipient got the same copy of the message.
::

    >>> messages = list(smtpd.messages)
    >>> len(messages)
    1

    >>> print messages[0].as_string()
    From: aperson@example.com
    To: test@example.com
    Subject: My first post
    Message-ID: <first>
    X-Peer: ...
    X-MailFrom: test-bounces@example.com
    X-RcptTo: cperson@example.com, bperson@example.com, aperson@example.com
    <BLANKLINE>
    First post!


Personalization
===============

Mailman supports sending individual messages to each recipient by
personalizing delivery.  This increases the bandwidth between Mailman and the
upstream mail server, and between the upstream mail server and the remote
recipient mail servers.  The benefit is that personalization provides for a
much better user experience, because the messages can be tailored for each
recipient.

    >>> from mailman.interfaces.mailinglist import Personalization
    >>> mlist.personalize = Personalization.individual
    >>> transaction.commit()

Now when we send the message, our mail server will get three copies instead of
just one.

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

Since we've done no other configuration, the only difference in the messages
is the recipient address.  Specifically, the Sender header is the same for all
recipients.
::

    >>> from operator import itemgetter
    >>> def show_headers(messages):
    ...     for message in sorted(messages, key=itemgetter('x-rcptto')):
    ...         print message['X-RcptTo'], message['X-MailFrom']

    >>> show_headers(messages)
    aperson@example.com   test-bounces@example.com
    bperson@example.com   test-bounces@example.com
    cperson@example.com   test-bounces@example.com


VERP
====

An even more interesting personalization opportunity arises if VERP_ is
enabled.  Here, Mailman takes advantage of the fact that it's sending
individualized messages anyway, so it also encodes the recipients address in
the Sender header.

.. _VERP: ../../mta/docs/verp.html


Forcing VERP
------------

A handler can force VERP by setting the ``verp`` key in the message metadata.
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     verp=True,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> show_headers(messages)
    aperson@example.com   test-bounces+aperson=example.com@example.com
    bperson@example.com   test-bounces+bperson=example.com@example.com
    cperson@example.com   test-bounces+cperson=example.com@example.com


VERP personalized deliveries
----------------------------

The site administrator can enable VERP whenever messages are personalized.

    >>> config.push('verp', """
    ... [mta]
    ... verp_personalized_deliveries: yes
    ... """)

Again, we get three individual messages, with VERP'd ``Sender`` headers.
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> show_headers(messages)
    aperson@example.com   test-bounces+aperson=example.com@example.com
    bperson@example.com   test-bounces+bperson=example.com@example.com
    cperson@example.com   test-bounces+cperson=example.com@example.com

    >>> config.pop('verp')
    >>> mlist.personalize = Personalization.none
    >>> transaction.commit()


VERP every once in a while
--------------------------

Perhaps personalization is too much of an overhead, but the list owners would
still like to occasionally get the benefits of VERP.  The site administrator
can enable occasional VERPing of messages every so often, by setting a
delivery interval.  Every N non-personalized deliveries turns on VERP for just
the next one.
::

    >>> config.push('verp occasionally', """
    ... [mta]
    ... verp_delivery_interval: 3
    ... """)

    # Reset the list's post_id, which is used to calculate the intervals.
    >>> mlist.post_id = 1
    >>> transaction.commit()

The first message is sent to the list, and it is neither personalized nor
VERP'd.
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    1

    >>> show_headers(messages)
    cperson@example.com, bperson@example.com, aperson@example.com
    test-bounces@example.com

    # Perform post-delivery bookkeeping.
    >>> after = config.handlers['after-delivery']
    >>> after.process(mlist, msg, msgdata)
    >>> transaction.commit()

The second message sent to the list is also not VERP'd.
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    1

    >>> show_headers(messages)
    cperson@example.com, bperson@example.com, aperson@example.com
    test-bounces@example.com

    # Perform post-delivery bookkeeping.
    >>> after.process(mlist, msg, msgdata)
    >>> transaction.commit()

The third message though is VERP'd.
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> show_headers(messages)
    aperson@example.com   test-bounces+aperson=example.com@example.com
    bperson@example.com   test-bounces+bperson=example.com@example.com
    cperson@example.com   test-bounces+cperson=example.com@example.com

    # Perform post-delivery bookkeeping.
    >>> after.process(mlist, msg, msgdata)
    >>> transaction.commit()

The next one is back to bulk delivery.
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    1

    >>> show_headers(messages)
    cperson@example.com, bperson@example.com, aperson@example.com
    test-bounces@example.com

    >>> config.pop('verp occasionally')


VERP every time
---------------

If the site administrator wants to enable VERP for every delivery, even if no
personalization is going on, they can set the interval to 1.
::

    >>> config.push('always verp', """
    ... [mta]
    ... verp_delivery_interval: 1
    ... """)

    # Reset the list's post_id, which is used to calculate the intervals.
    >>> mlist.post_id = 1
    >>> transaction.commit()

The first message is VERP'd.
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> show_headers(messages)
    aperson@example.com   test-bounces+aperson=example.com@example.com
    bperson@example.com   test-bounces+bperson=example.com@example.com
    cperson@example.com   test-bounces+cperson=example.com@example.com

    # Perform post-delivery bookkeeping.
    >>> after.process(mlist, msg, msgdata)
    >>> transaction.commit()

As is the second message.
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> show_headers(messages)
    aperson@example.com   test-bounces+aperson=example.com@example.com
    bperson@example.com   test-bounces+bperson=example.com@example.com
    cperson@example.com   test-bounces+cperson=example.com@example.com

    # Perform post-delivery bookkeeping.
    >>> after.process(mlist, msg, msgdata)
    >>> transaction.commit()

And the third message.
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    3

    >>> show_headers(messages)
    aperson@example.com   test-bounces+aperson=example.com@example.com
    bperson@example.com   test-bounces+bperson=example.com@example.com
    cperson@example.com   test-bounces+cperson=example.com@example.com

    # Perform post-delivery bookkeeping.
    >>> after.process(mlist, msg, msgdata)
    >>> transaction.commit()

    >>> config.pop('always verp')


Never VERP
----------

Similarly, the site administrator can disable occasional VERP'ing of
non-personalized messages by setting the interval to zero.
::

    >>> config.push('never verp', """
    ... [mta]
    ... verp_delivery_interval: 0
    ... """)

    # Reset the list's post_id, which is used to calculate the intervals.
    >>> mlist.post_id = 1
    >>> transaction.commit()

Neither the first message...
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    1

    >>> show_headers(messages)
    cperson@example.com, bperson@example.com, aperson@example.com
    test-bounces@example.com

...nor the second message is VERP'd.
::

    >>> ignore = outgoing_queue.enqueue(
    ...     msg, msgdata,
    ...     listname=mlist.fqdn_listname)
    >>> outgoing.run()
    >>> messages = list(smtpd.messages)
    >>> len(messages)
    1

    >>> show_headers(messages)
    cperson@example.com, bperson@example.com, aperson@example.com
    test-bounces@example.com
