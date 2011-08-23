==================
Moderator requests
==================

Various actions will be held for moderator approval, such as subscriptions to
closed lists, or postings by non-members.  The requests database is the low
level interface to these actions requiring approval.

Here is a helper function for printing out held requests.

    >>> def show_holds(requests):
    ...     for request in requests.held_requests:
    ...         key, data = requests.get_request(request.id)
    ...         print request.id, str(request.request_type), key
    ...         if data is not None:
    ...             for key in sorted(data):
    ...                 print '    {0}: {1}'.format(key, data[key])

And another helper for displaying messages in the virgin queue.

    >>> virginq = config.switchboards['virgin']
    >>> def dequeue(whichq=None, expected_count=1):
    ...     if whichq is None:
    ...         whichq = virginq
    ...     assert len(whichq.files) == expected_count, (
    ...         'Unexpected file count: %d' % len(whichq.files))
    ...     filebase = whichq.files[0]
    ...     qmsg, qdata = whichq.dequeue(filebase)
    ...     whichq.finish(filebase)
    ...     return qmsg, qdata


Mailing list centric
====================

A set of requests are always related to a particular mailing list, so given a
mailing list you need to get its requests object.
::

    >>> from mailman.interfaces.requests import IListRequests, IRequests
    >>> from zope.component import getUtility
    >>> from zope.interface.verify import verifyObject

    >>> mlist = create_list('test@example.com')
    >>> requests = getUtility(IRequests).get_list_requests(mlist)
    >>> verifyObject(IListRequests, requests)
    True
    >>> requests.mailing_list
    <mailing list "test@example.com" at ...>


Holding requests
================

The list's requests database starts out empty.

    >>> requests.count
    0
    >>> dump_list(requests.held_requests)
    *Empty*

At the lowest level, the requests database is very simple.  Holding a request
requires a request type (as an enum value), a key, and an optional dictionary
of associated data.  The request database assigns no semantics to the held
data, except for the request type.  Here we hold some simple bits of data.

    >>> from mailman.interfaces.requests import RequestType
    >>> id_1 = requests.hold_request(RequestType.held_message,   'hold_1')
    >>> id_2 = requests.hold_request(RequestType.subscription,   'hold_2')
    >>> id_3 = requests.hold_request(RequestType.unsubscription, 'hold_3')
    >>> id_4 = requests.hold_request(RequestType.held_message,   'hold_4')
    >>> id_1, id_2, id_3, id_4
    (1, 2, 3, 4)

And of course, now we can see that there are four requests being held.

    >>> requests.count
    4
    >>> requests.count_of(RequestType.held_message)
    2
    >>> requests.count_of(RequestType.subscription)
    1
    >>> requests.count_of(RequestType.unsubscription)
    1
    >>> show_holds(requests)
    1 RequestType.held_message hold_1
    2 RequestType.subscription hold_2
    3 RequestType.unsubscription hold_3
    4 RequestType.held_message hold_4

If we try to hold a request with a bogus type, we get an exception.

    >>> requests.hold_request(5, 'foo')
    Traceback (most recent call last):
    ...
    TypeError: 5

We can hold requests with additional data.

    >>> data = dict(foo='yes', bar='no')
    >>> id_5 = requests.hold_request(RequestType.held_message, 'hold_5', data)
    >>> id_5
    5
    >>> requests.count
    5
    >>> show_holds(requests)
    1 RequestType.held_message hold_1
    2 RequestType.subscription hold_2
    3 RequestType.unsubscription hold_3
    4 RequestType.held_message hold_4
    5 RequestType.held_message hold_5
        bar: no
        foo: yes


Getting requests
================

We can ask the requests database for a specific request, by providing the id
of the request data we want.  This returns a 2-tuple of the key and data we
originally held.

    >>> key, data = requests.get_request(2)
    >>> print key
    hold_2

Because we did not store additional data with request 2, it comes back as None
now.

    >>> print data
    None

However, if we ask for a request that had data, we'd get it back now.

    >>> key, data = requests.get_request(5)
    >>> print key
    hold_5
    >>> dump_msgdata(data)
    bar: no
    foo: yes

If we ask for a request that is not in the database, we get None back.

    >>> print requests.get_request(801)
    None


Iterating over requests
=======================

To make it easier to find specific requests, the list requests can be iterated
over by type.

    >>> requests.count_of(RequestType.held_message)
    3
    >>> for request in requests.of_type(RequestType.held_message):
    ...     assert request.request_type is RequestType.held_message
    ...     key, data = requests.get_request(request.id)
    ...     print request.id, key
    ...     if data is not None:
    ...         for key in sorted(data):
    ...             print '    {0}: {1}'.format(key, data[key])
    1 hold_1
    4 hold_4
    5 hold_5
    bar: no
    foo: yes


Deleting requests
=================

Once a specific request has been handled, it will be deleted from the requests
database.

    >>> requests.delete_request(2)
    >>> requests.count
    4
    >>> show_holds(requests)
    1 RequestType.held_message hold_1
    3 RequestType.unsubscription hold_3
    4 RequestType.held_message hold_4
    5 RequestType.held_message hold_5
        bar: no
        foo: yes
    >>> print requests.get_request(2)
    None

We get an exception if we ask to delete a request that isn't in the database.

    >>> requests.delete_request(801)
    Traceback (most recent call last):
    ...
    KeyError: 801

For the next section, we first clean up all the current requests.

    >>> for request in requests.held_requests:
    ...     requests.delete_request(request.id)
    >>> requests.count
    0


Application support
===================

There are several higher level interfaces available in the ``mailman.app``
package which can be used to hold messages, subscription, and unsubscriptions.
There are also interfaces for disposing of these requests in an application
specific and consistent way.

    >>> from mailman.app import moderator


Holding messages
================

For this section, we need a mailing list and at least one message.

    >>> mlist = create_list('alist@example.com')
    >>> mlist.preferred_language = 'en'
    >>> mlist.real_name = 'A Test List'
    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... To: alist@example.com
    ... Subject: Something important
    ...
    ... Here's something important about our mailing list.
    ... """)

Holding a message means keeping a copy of it that a moderator must approve
before the message is posted to the mailing list.  To hold the message, you
must supply the message, message metadata, and a text reason for the hold.  In
this case, we won't include any additional metadata.

    >>> id_1 = moderator.hold_message(mlist, msg, {}, 'Needs approval')
    >>> requests.get_request(id_1) is not None
    True

We can also hold a message with some additional metadata.
::

    # Delete the Message-ID from the previous hold so we don't try to store
    # collisions in the message storage.
    >>> del msg['message-id']
    >>> msgdata = dict(sender='aperson@example.com',
    ...                approved=True,
    ...                received_time=123.45)
    >>> id_2 = moderator.hold_message(mlist, msg, msgdata, 'Feeling ornery')
    >>> requests.get_request(id_2) is not None
    True

Once held, the moderator can select one of several dispositions.  The most
trivial is to simply defer a decision for now.

    >>> from mailman.interfaces.action import Action
    >>> moderator.handle_message(mlist, id_1, Action.defer)
    >>> requests.get_request(id_1) is not None
    True

The moderator can also discard the message.  This is often done with spam.
Bye bye message!

    >>> moderator.handle_message(mlist, id_1, Action.discard)
    >>> print requests.get_request(id_1)
    None
    >>> virginq.files
    []

The message can be rejected, meaning it is bounced back to the sender.

    >>> moderator.handle_message(mlist, id_2, Action.reject, 'Off topic')
    >>> print requests.get_request(id_2)
    None
    >>> qmsg, qdata = dequeue()
    >>> print qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: Request to mailing list "A Test List" rejected
    From: alist-bounces@example.com
    To: aperson@example.org
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    Your request to the alist@example.com mailing list
    <BLANKLINE>
        Posting of your message titled "Something important"
    <BLANKLINE>
    has been rejected by the list moderator.  The moderator gave the
    following reason for rejecting your request:
    <BLANKLINE>
    "Off topic"
    <BLANKLINE>
    Any questions or comments should be directed to the list administrator
    at:
    <BLANKLINE>
        alist-owner@example.com
    <BLANKLINE>
    >>> dump_msgdata(qdata)
    _parsemsg           : False
    listname            : alist@example.com
    nodecorate          : True
    recipients          : set([u'aperson@example.org'])
    reduced_list_headers: True
    version             : 3

Or the message can be approved.  This actually places the message back into
the incoming queue for further processing, however the message metadata
indicates that the message has been approved.

    >>> id_3 = moderator.hold_message(mlist, msg, msgdata, 'Needs approval')
    >>> moderator.handle_message(mlist, id_3, Action.accept)
    >>> inq = config.switchboards['pipeline']
    >>> qmsg, qdata = dequeue(inq)
    >>> print qmsg.as_string()
    From: aperson@example.org
    To: alist@example.com
    Subject: Something important
    Message-ID: ...
    X-Message-ID-Hash: ...
    X-Mailman-Approved-At: ...
    <BLANKLINE>
    Here's something important about our mailing list.
    <BLANKLINE>
    >>> dump_msgdata(qdata)
    _parsemsg         : False
    approved          : True
    moderator_approved: True
    sender            : aperson@example.com
    version           : 3

In addition to any of the above dispositions, the message can also be
preserved for further study.  Ordinarily the message is removed from the
global message store after its disposition (though approved messages may be
re-added to the message store).  When handling a message, we can tell the
moderator interface to also preserve a copy, essentially telling it not to
delete the message from the storage.  First, without the switch, the message
is deleted.
::

    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... To: alist@example.com
    ... Subject: Something important
    ... Message-ID: <12345>
    ...
    ... Here's something important about our mailing list.
    ... """)
    >>> id_4 = moderator.hold_message(mlist, msg, {}, 'Needs approval')
    >>> moderator.handle_message(mlist, id_4, Action.discard)

    >>> from mailman.interfaces.messages import IMessageStore
    >>> from zope.component import getUtility
    >>> message_store = getUtility(IMessageStore)

    >>> print message_store.get_message_by_id('<12345>')
    None

But if we ask to preserve the message when we discard it, it will be held in
the message store after disposition.

    >>> id_4 = moderator.hold_message(mlist, msg, {}, 'Needs approval')
    >>> moderator.handle_message(mlist, id_4, Action.discard, preserve=True)
    >>> stored_msg = message_store.get_message_by_id('<12345>')
    >>> print stored_msg.as_string()
    From: aperson@example.org
    To: alist@example.com
    Subject: Something important
    Message-ID: <12345>
    X-Message-ID-Hash: 4CF7EAU3SIXBPXBB5S6PEUMO62MWGQN6
    <BLANKLINE>
    Here's something important about our mailing list.
    <BLANKLINE>

Orthogonal to preservation, the message can also be forwarded to another
address.  This is helpful for getting the message into the inbox of one of the
moderators.
::

    # Set a new Message-ID from the previous hold so we don't try to store
    # collisions in the message storage.
    >>> del msg['message-id']
    >>> msg['Message-ID'] = '<abcde>'
    >>> id_4 = moderator.hold_message(mlist, msg, {}, 'Needs approval')
    >>> moderator.handle_message(mlist, id_4, Action.discard,
    ...                          forward=['zperson@example.com'])
    >>> qmsg, qdata = dequeue()
    >>> print qmsg.as_string()
    Subject: Forward of moderated message
    From: alist-bounces@example.com
    To: zperson@example.com
    MIME-Version: 1.0
    Content-Type: message/rfc822
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    From: aperson@example.org
    To: alist@example.com
    Subject: Something important
    Message-ID: <abcde>
    X-Message-ID-Hash: EN2R5UQFMOUTCL44FLNNPLSXBIZW62ER
    <BLANKLINE>
    Here's something important about our mailing list.
    <BLANKLINE>
    >>> dump_msgdata(qdata)
    _parsemsg           : False
    listname            : alist@example.com
    nodecorate          : True
    recipients          : [u'zperson@example.com']
    reduced_list_headers: True
    version             : 3


Holding subscription requests
=============================

For closed lists, subscription requests will also be held for moderator
approval.  In this case, several pieces of information related to the
subscription must be provided, including the subscriber's address and real
name, their password (possibly hashed), what kind of delivery option they are
choosing and their preferred language.

    >>> from mailman.interfaces.member import DeliveryMode
    >>> mlist.admin_immed_notify = False
    >>> id_3 = moderator.hold_subscription(mlist,
    ...     'bperson@example.org', 'Ben Person',
    ...     '{NONE}abcxyz', DeliveryMode.regular, 'en')
    >>> requests.get_request(id_3) is not None
    True

In the above case the mailing list was not configured to send the list
moderators a notice about the hold, so no email message is in the virgin
queue.

    >>> virginq.files
    []

But if we set the list up to notify the list moderators immediately when a
message is held for approval, there will be a message placed in the virgin
queue when the message is held.

    >>> mlist.admin_immed_notify = True
    >>> # XXX This will almost certainly change once we've worked out the web
    >>> # space layout for mailing lists now.
    >>> id_4 = moderator.hold_subscription(mlist,
    ...     'cperson@example.org', 'Claire Person',
    ...     '{NONE}zyxcba', DeliveryMode.regular, 'en')
    >>> requests.get_request(id_4) is not None
    True
    >>> qmsg, qdata = dequeue()
    >>> print qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: New subscription request to list A Test List from
     cperson@example.org
    From: alist-owner@example.com
    To: alist-owner@example.com
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    Your authorization is required for a mailing list subscription request
    approval:
    <BLANKLINE>
        For:  cperson@example.org
        List: alist@example.com
    <BLANKLINE>
    At your convenience, visit:
    <BLANKLINE>
        http://lists.example.com/admindb/alist@example.com
    <BLANKLINE>
    to process the request.
    <BLANKLINE>
    >>> dump_msgdata(qdata)
    _parsemsg           : False
    listname            : alist@example.com
    nodecorate          : True
    recipients          : set([u'alist-owner@example.com'])
    reduced_list_headers: True
    tomoderators        : True
    version             : 3

Once held, the moderator can select one of several dispositions.  The most
trivial is to simply defer a decision for now.

    >>> moderator.handle_subscription(mlist, id_3, Action.defer)
    >>> requests.get_request(id_3) is not None
    True

The held subscription can also be discarded.

    >>> moderator.handle_subscription(mlist, id_3, Action.discard)
    >>> print requests.get_request(id_3)
    None

The request can be rejected, in which case a message is sent to the
subscriber.

    >>> moderator.handle_subscription(mlist, id_4, Action.reject,
    ...     'This is a closed list')
    >>> print requests.get_request(id_4)
    None
    >>> qmsg, qdata = dequeue()
    >>> print qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: Request to mailing list "A Test List" rejected
    From: alist-bounces@example.com
    To: cperson@example.org
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    Your request to the alist@example.com mailing list
    <BLANKLINE>
        Subscription request
    <BLANKLINE>
    has been rejected by the list moderator.  The moderator gave the
    following reason for rejecting your request:
    <BLANKLINE>
    "This is a closed list"
    <BLANKLINE>
    Any questions or comments should be directed to the list administrator
    at:
    <BLANKLINE>
        alist-owner@example.com
    <BLANKLINE>
    >>> dump_msgdata(qdata)
    _parsemsg           : False
    listname            : alist@example.com
    nodecorate          : True
    recipients          : set([u'cperson@example.org'])
    reduced_list_headers: True
    version             : 3

The subscription can also be accepted.  This subscribes the address to the
mailing list.

    >>> mlist.send_welcome_msg = True
    >>> id_4 = moderator.hold_subscription(mlist,
    ...     'fperson@example.org', 'Frank Person',
    ...     '{NONE}abcxyz', DeliveryMode.regular, 'en')

A message will be sent to the moderators telling them about the held
subscription and the fact that they may need to approve it.

    >>> qmsg, qdata = dequeue()
    >>> print qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: New subscription request to list A Test List from
     fperson@example.org
    From: alist-owner@example.com
    To: alist-owner@example.com
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    Your authorization is required for a mailing list subscription request
    approval:
    <BLANKLINE>
        For:  fperson@example.org
        List: alist@example.com
    <BLANKLINE>
    At your convenience, visit:
    <BLANKLINE>
        http://lists.example.com/admindb/alist@example.com
    <BLANKLINE>
    to process the request.
    <BLANKLINE>
    >>> dump_msgdata(qdata)
    _parsemsg           : False
    listname            : alist@example.com
    nodecorate          : True
    recipients          : set([u'alist-owner@example.com'])
    reduced_list_headers: True
    tomoderators        : True
    version             : 3

Accept the subscription request.

    >>> mlist.admin_notify_mchanges = True
    >>> moderator.handle_subscription(mlist, id_4, Action.accept)

There are now two messages in the virgin queue.  One is a welcome message
being sent to the user and the other is a subscription notification that is
sent to the moderators.  The only good way to tell which is which is to look
at the recipient list.

    >>> qmsg_1, qdata_1 = dequeue(expected_count=2)
    >>> qmsg_2, qdata_2 = dequeue()
    >>> if 'fperson@example.org' in qdata_1['recipients']:
    ...     # The first message is the welcome message
    ...     welcome_qmsg = qmsg_1
    ...     welcome_qdata = qdata_1
    ...     admin_qmsg = qmsg_2
    ...     admin_qdata = qdata_2
    ... else:
    ...     welcome_qmsg = qmsg_2
    ...     welcome_qdata = qdata_2
    ...     admin_qmsg = qmsg_1
    ...     admin_qdata = qdata_1

The welcome message is sent to the person who just subscribed.

    >>> print welcome_qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: Welcome to the "A Test List" mailing list
    From: alist-request@example.com
    To: fperson@example.org
    X-No-Archive: yes
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    Welcome to the "A Test List" mailing list!
    <BLANKLINE>
    To post to this list, send your email to:
    <BLANKLINE>
      alist@example.com
    <BLANKLINE>
    General information about the mailing list is at:
    <BLANKLINE>
      http://lists.example.com/listinfo/alist@example.com
    <BLANKLINE>
    If you ever want to unsubscribe or change your options (eg, switch to
    or from digest mode, change your password, etc.), visit your
    subscription page at:
    <BLANKLINE>
      http://example.com/fperson@example.org
    <BLANKLINE>
    You can also make such adjustments via email by sending a message to:
    <BLANKLINE>
      alist-request@example.com
    <BLANKLINE>
    with the word 'help' in the subject or body (don't include the
    quotes), and you will get back a message with instructions.  You will
    need your password to change your options, but for security purposes,
    this email is not included here.  There is also a button on your
    options page that will send your current password to you.
    <BLANKLINE>
    >>> dump_msgdata(welcome_qdata)
    _parsemsg           : False
    listname            : alist@example.com
    nodecorate          : True
    recipients          : set([u'fperson@example.org'])
    reduced_list_headers: True
    verp                : False
    version             : 3

The admin message is sent to the moderators.

    >>> print admin_qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: A Test List subscription notification
    From: changeme@example.com
    To: alist-owner@example.com
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    Frank Person <fperson@example.org> has been successfully subscribed to
    A Test List.
    <BLANKLINE>
    >>> dump_msgdata(admin_qdata)
    _parsemsg           : False
    envsender           : changeme@example.com
    listname            : alist@example.com
    nodecorate          : True
    recipients          : set([])
    reduced_list_headers: True
    version             : 3

Frank Person is now a member of the mailing list.
::

    >>> member = mlist.members.get_member('fperson@example.org')
    >>> member
    <Member: Frank Person <fperson@example.org>
             on alist@example.com as MemberRole.member>
    >>> member.preferred_language
    <Language [en] English (USA)>
    >>> print member.delivery_mode
    DeliveryMode.regular
    >>> print member.user.real_name
    Frank Person
    >>> print member.user.password
    {NONE}abcxyz


Holding unsubscription requests
===============================

Some lists, though it is rare, require moderator approval for unsubscriptions.
In this case, only the unsubscribing address is required.  Like subscriptions,
unsubscription holds can send the list's moderators an immediate
notification.
::


    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)

    >>> mlist.admin_immed_notify = False
    >>> from mailman.interfaces.member import MemberRole
    >>> user_1 = user_manager.create_user('gperson@example.com')
    >>> address_1 = list(user_1.addresses)[0]
    >>> mlist.subscribe(address_1, MemberRole.member)
    <Member: gperson@example.com on alist@example.com as MemberRole.member>

    >>> user_2 = user_manager.create_user('hperson@example.com')
    >>> address_2 = list(user_2.addresses)[0]
    >>> mlist.subscribe(address_2, MemberRole.member)
    <Member: hperson@example.com on alist@example.com as MemberRole.member>

    >>> id_5 = moderator.hold_unsubscription(mlist, 'gperson@example.com')
    >>> requests.get_request(id_5) is not None
    True
    >>> virginq.files
    []
    >>> mlist.admin_immed_notify = True
    >>> id_6 = moderator.hold_unsubscription(mlist, 'hperson@example.com')
    >>> qmsg, qdata = dequeue()
    >>> print qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: New unsubscription request from A Test List by hperson@example.com
    From: alist-owner@example.com
    To: alist-owner@example.com
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    Your authorization is required for a mailing list unsubscription
    request approval:
    <BLANKLINE>
        By:   hperson@example.com
        From: alist@example.com
    <BLANKLINE>
    At your convenience, visit:
    <BLANKLINE>
        http://lists.example.com/admindb/alist@example.com
    <BLANKLINE>
    to process the request.
    <BLANKLINE>
    >>> dump_msgdata(qdata)
    _parsemsg           : False
    listname            : alist@example.com
    nodecorate          : True
    recipients          : set([u'alist-owner@example.com'])
    reduced_list_headers: True
    tomoderators        : True
    version             : 3

There are now two addresses with held unsubscription requests.  As above, one
of the actions we can take is to defer to the decision.

    >>> moderator.handle_unsubscription(mlist, id_5, Action.defer)
    >>> requests.get_request(id_5) is not None
    True

The held unsubscription can also be discarded, and the member will remain
subscribed.

    >>> moderator.handle_unsubscription(mlist, id_5, Action.discard)
    >>> print requests.get_request(id_5)
    None
    >>> mlist.members.get_member('gperson@example.com')
    <Member: gperson@example.com on alist@example.com as MemberRole.member>

The request can be rejected, in which case a message is sent to the member,
and the person remains a member of the mailing list.
::

    >>> moderator.handle_unsubscription(mlist, id_6, Action.reject,
    ...     'This list is a prison.')
    >>> print requests.get_request(id_6)
    None
    >>> qmsg, qdata = dequeue()
    >>> print qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: Request to mailing list "A Test List" rejected
    From: alist-bounces@example.com
    To: hperson@example.com
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    Your request to the alist@example.com mailing list
    <BLANKLINE>
        Unsubscription request
    <BLANKLINE>
    has been rejected by the list moderator.  The moderator gave the
    following reason for rejecting your request:
    <BLANKLINE>
    "This list is a prison."
    <BLANKLINE>
    Any questions or comments should be directed to the list administrator
    at:
    <BLANKLINE>
        alist-owner@example.com
    <BLANKLINE>
    >>> dump_msgdata(qdata)
    _parsemsg           : False
    listname            : alist@example.com
    nodecorate          : True
    recipients          : set([u'hperson@example.com'])
    reduced_list_headers: True
    version             : 3

    >>> mlist.members.get_member('hperson@example.com')
    <Member: hperson@example.com on alist@example.com as MemberRole.member>

The unsubscription request can also be accepted.  This removes the member from
the mailing list.

    >>> mlist.send_goodbye_msg = True
    >>> mlist.goodbye_msg = 'So long!'
    >>> mlist.admin_immed_notify = False
    >>> id_7 = moderator.hold_unsubscription(mlist, 'gperson@example.com')
    >>> moderator.handle_unsubscription(mlist, id_7, Action.accept)
    >>> print mlist.members.get_member('gperson@example.com')
    None

There are now two messages in the virgin queue, one to the member who was just
unsubscribed and another to the moderators informing them of this membership
change.

    >>> qmsg_1, qdata_1 = dequeue(expected_count=2)
    >>> qmsg_2, qdata_2 = dequeue()
    >>> if 'gperson@example.com' in qdata_1['recipients']:
    ...     # The first message is the goodbye message
    ...     goodbye_qmsg = qmsg_1
    ...     goodbye_qdata = qdata_1
    ...     admin_qmsg = qmsg_2
    ...     admin_qdata = qdata_2
    ... else:
    ...     goodbye_qmsg = qmsg_2
    ...     goodbye_qdata = qdata_2
    ...     admin_qmsg = qmsg_1
    ...     admin_qdata = qdata_1

The goodbye message...

    >>> print goodbye_qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: You have been unsubscribed from the A Test List mailing list
    From: alist-bounces@example.com
    To: gperson@example.com
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    So long!
    <BLANKLINE>
    >>> dump_msgdata(goodbye_qdata)
    _parsemsg           : False
    listname            : alist@example.com
    nodecorate          : True
    recipients          : set([u'gperson@example.com'])
    reduced_list_headers: True
    verp                : False
    version             : 3

...and the admin message.

    >>> print admin_qmsg.as_string()
    MIME-Version: 1.0
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    Subject: A Test List unsubscription notification
    From: changeme@example.com
    To: alist-owner@example.com
    Message-ID: ...
    Date: ...
    Precedence: bulk
    <BLANKLINE>
    gperson@example.com has been removed from A Test List.
    <BLANKLINE>
    >>> dump_msgdata(admin_qdata)
    _parsemsg           : False
    envsender           : changeme@example.com
    listname            : alist@example.com
    nodecorate          : True
    recipients          : set([])
    reduced_list_headers: True
    version             : 3
