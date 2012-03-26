============================
Membership changes via email
============================

Membership changes such as joining and leaving a mailing list, can be effected
via the email interface.  The Mailman email commands ``join``, ``leave``, and
``confirm`` are used.


Joining a mailing list
======================

The mail command ``join`` subscribes an email address to the mailing list.
``subscribe`` is an alias for ``join``.

    >>> from mailman.commands.eml_membership import Join
    >>> from mailman.utilities.string import wrap
    >>> join = Join()
    >>> print join.name
    join
    >>> print wrap(join.description)
    You will be asked to confirm your subscription request and you may be
    issued a provisional password.
    <BLANKLINE>
    By using the 'digest' option, you can specify whether you want digest
    delivery or not.  If not specified, the mailing list's default
    delivery mode will be used.
    >>> print join.argument_description
    [digest=<no|mime|plain>]


No address to join
------------------

    >>> mlist = create_list('alpha@example.com')
    >>> mlist.send_welcome_message = False

When no address argument is given, the message's From address will be used.
If that's missing though, then an error is returned.
::

    >>> from mailman.runners.command import Results
    >>> results = Results()

    >>> from mailman.email.message import Message
    >>> print join.process(mlist, Message(), {}, (), results)
    ContinueProcessing.no
    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    join: No valid address found to subscribe
    <BLANKLINE>

The ``subscribe`` command is an alias.

    >>> from mailman.commands.eml_membership import Subscribe
    >>> subscribe = Subscribe()
    >>> print subscribe.name
    subscribe
    >>> results = Results()
    >>> print subscribe.process(mlist, Message(), {}, (), results)
    ContinueProcessing.no
    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    subscribe: No valid address found to subscribe
    <BLANKLINE>


Joining the sender
------------------

When the message has a From field, that address will be subscribed.

    >>> msg = message_from_string("""\
    ... From: Anne Person <anne@example.com>
    ...
    ... """)
    >>> results = Results()
    >>> print join.process(mlist, msg, {}, (), results)
    ContinueProcessing.yes
    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    Confirmation email sent to Anne Person <anne@example.com>
    <BLANKLINE>

Anne is not yet a member because she must confirm her subscription request
first.

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)
    >>> print user_manager.get_user('anne@example.com')
    None

Mailman has sent her the confirmation message.

    >>> from mailman.testing.helpers import get_queue_messages
    >>> items = get_queue_messages('virgin')
    >>> len(items)
    1
    >>> print items[0].msg.as_string()
    MIME-Version: 1.0
    ...
    Subject: confirm ...
    From: alpha-confirm+...@example.com
    To: anne@example.com
    ...
    <BLANKLINE>
    Email Address Registration Confirmation
    <BLANKLINE>
    Hello, this is the GNU Mailman server at example.com.
    <BLANKLINE>
    We have received a registration request for the email address
    <BLANKLINE>
        anne@example.com
    <BLANKLINE>
    Before you can start using GNU Mailman at this site, you must first
    confirm that this is your email address.  You can do this by replying to
    this message, keeping the Subject header intact.  Or you can visit this
    web page
    <BLANKLINE>
        http://lists.example.com/confirm/...
    <BLANKLINE>
    If you do not wish to register this email address simply disregard this
    message.  If you think you are being maliciously subscribed to the list, or
    have any other questions, you may contact
    <BLANKLINE>
        postmaster@example.com
    <BLANKLINE>

Once Anne confirms her registration, she will be made a member of the mailing
list.
::

    >>> def extract_token(message):
    ...     return str(message['subject']).split()[1].strip()
    >>> token = extract_token(items[0].msg)

    >>> from mailman.commands.eml_confirm import Confirm
    >>> confirm = Confirm()
    >>> msg = message_from_string("""\
    ... To: alpha-confirm+{token}@example.com
    ... From: anne@example.com
    ... Subject: Re: confirm {token}
    ...
    ... """.format(token=token))

    >>> results = Results()
    >>> print confirm.process(mlist, msg, {}, (token,), results)
    ContinueProcessing.yes
    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    Confirmed
    <BLANKLINE>

    >>> user = user_manager.get_user('anne@example.com')
    >>> print user.display_name
    Anne Person
    >>> list(user.addresses)
    [<Address: Anne Person <anne@example.com> [verified] at ...>]

Anne is also now a member of the mailing list.

    >>> mlist.members.get_member('anne@example.com')
    <Member: Anne Person <anne@example.com>
             on alpha@example.com as MemberRole.member>


Joining a second list
---------------------

    >>> mlist_2 = create_list('baker@example.com')
    >>> msg = message_from_string("""\
    ... From: Anne Person <anne@example.com>
    ...
    ... """)
    >>> print join.process(mlist_2, msg, {}, (), Results())
    ContinueProcessing.yes

Anne of course, is still registered.

    >>> print user_manager.get_user('anne@example.com')
    <User "Anne Person" (...) at ...>

But she is not a member of the mailing list.

    >>> print mlist_2.members.get_member('anne@example.com')
    None

One Anne confirms this subscription, she becomes a member of the mailing
list.
::

    >>> items = get_queue_messages('virgin')
    >>> len(items)
    1
    >>> token = extract_token(items[0].msg)
    >>> msg = message_from_string("""\
    ... To: baker-confirm+{token}@example.com
    ... From: anne@example.com
    ... Subject: Re: confirm {token}
    ...
    ... """.format(token=token))

    >>> results = Results()
    >>> print confirm.process(mlist_2, msg, {}, (token,), results)
    ContinueProcessing.yes
    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    Confirmed
    <BLANKLINE>

    >>> print mlist_2.members.get_member('anne@example.com')
    <Member: Anne Person <anne@example.com>
             on baker@example.com as MemberRole.member>


Leaving a mailing list
======================

The mail command ``leave`` unsubscribes an email address from the mailing
list.  ``unsubscribe`` is an alias for ``leave``.

    >>> from mailman.commands.eml_membership import Leave
    >>> leave = Leave()
    >>> print leave.name
    leave
    >>> print leave.description
    Leave this mailing list.
    <BLANKLINE>
    You may be asked to confirm your request.

Anne is a member of the ``baker@example.com`` mailing list, when she decides
to leave it.  She sends a message to the ``-leave`` address for the list and
is sent a confirmation message for her request.

    >>> results = Results()
    >>> print leave.process(mlist_2, msg, {}, (), results)
    ContinueProcessing.yes
    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    Anne Person <anne@example.com> left baker@example.com
    <BLANKLINE>

Anne is no longer a member of the mailing list.

    >>> print mlist_2.members.get_member('anne@example.com')
    None

Anne does not need to leave a mailing list with the same email address she's
subscribe with.  Any of her registered, linked, and validated email addresses
will do.
::

    >>> anne = user_manager.get_user('anne@example.com')
    >>> address = anne.register('anne.person@example.org')

    >>> results = Results()
    >>> print mlist.members.get_member('anne@example.com')
    <Member: Anne Person <anne@example.com>
             on alpha@example.com as MemberRole.member>

    >>> msg = message_from_string("""\
    ... To: alpha-leave@example.com
    ... From: anne.person@example.org
    ...
    ... """)

Since Anne's alternative address has not yet been verified, it can't be used
to unsubscribe Anne from the alpha mailing list.
::

    >>> print leave.process(mlist, msg, {}, (), results)
    ContinueProcessing.no

    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    Invalid or unverified email address: anne.person@example.org
    <BLANKLINE>

    >>> print mlist.members.get_member('anne@example.com')
    <Member: Anne Person <anne@example.com>
             on alpha@example.com as MemberRole.member>

Once Anne has verified her alternative address though, it can be used to
unsubscribe her from the list.
::

    >>> from mailman.utilities.datetime import now
    >>> address.verified_on = now()

    >>> results = Results()
    >>> print leave.process(mlist, msg, {}, (), results)
    ContinueProcessing.yes

    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    Anne Person <anne.person@example.org> left alpha@example.com
    <BLANKLINE>

    >>> print mlist.members.get_member('anne@example.com')
    None


Confirmations
=============

Bart wants to join the alpha list, so he sends his subscription request.
::

    >>> msg = message_from_string("""\
    ... From: Bart Person <bart@example.com>
    ...
    ... """)

    >>> print join.process(mlist, msg, {}, (), Results())
    ContinueProcessing.yes

There are two messages in the virgin queue, one of which is the confirmation
message.

    >>> for item in get_queue_messages('virgin'):
    ...     if str(item.msg['subject']).startswith('confirm'):
    ...         break
    ... else:
    ...     raise AssertionError('No confirmation message')
    >>> token = extract_token(item.msg)

Bart is still not a user.

    >>> print user_manager.get_user('bart@example.com')
    None

Bart replies to the original message, specifically keeping the Subject header
intact except for any prefix.  Mailman matches the token and confirms Bart as
a user of the system.
::

    >>> msg = message_from_string("""\
    ... From: Bart Person <bart@example.com>
    ... To: alpha-confirm+{token}@example.com
    ... Subject: Re: confirm {token}
    ...
    ... """.format(token=token))

    >>> results = Results()
    >>> print confirm.process(mlist, msg, {}, (token,), results)
    ContinueProcessing.yes

    >>> print unicode(results)
    The results of your email command are provided below.
    <BLANKLINE>
    Confirmed
    <BLANKLINE>

Now Bart is a user...

    >>> print user_manager.get_user('bart@example.com')
    <User "Bart Person" (...) at ...>

...and a member of the mailing list.

    >>> print mlist.members.get_member('bart@example.com')
    <Member: Bart Person <bart@example.com>
             on alpha@example.com as MemberRole.member>
