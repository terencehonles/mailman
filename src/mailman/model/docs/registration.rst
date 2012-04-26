====================
Address registration
====================

Before users can join a mailing list, they must first register with Mailman.
The only thing they must supply is an email address, although there is
additional information they may supply.  All registered email addresses must
be verified before Mailman will send them any list traffic.

The ``IUserManager`` manages users, but it does so at a fairly low level.
Specifically, it does not handle verifications, email address syntax validity
checks, etc.  The ``IRegistrar`` is the interface to the object handling all
this stuff.

    >>> from mailman.interfaces.registrar import IRegistrar
    >>> from zope.component import getUtility
    >>> registrar = getUtility(IRegistrar)

Here is a helper function to check the token strings.

    >>> def check_token(token):
    ...     assert isinstance(token, basestring), 'Not a string'
    ...     assert len(token) == 40, 'Unexpected length: %d' % len(token)
    ...     assert token.isalnum(), 'Not alphanumeric'
    ...     print 'ok'

Here is a helper function to extract tokens from confirmation messages.

    >>> import re
    >>> cre = re.compile('http://lists.example.com/confirm/(.*)')
    >>> def extract_token(msg):
    ...     mo = cre.search(msg.get_payload())
    ...     return mo.group(1)


Invalid email addresses
=======================

Addresses are registered within the context of a mailing list, mostly so that
confirmation emails can come from some place.  You also need the email
address of the user who is registering.

    >>> mlist = create_list('alpha@example.com')
    >>> mlist.send_welcome_message = False

Some amount of sanity checks are performed on the email address, although
honestly, not as much as probably should be done.  Still, some patently bad
addresses are rejected outright.

    >>> registrar.register(mlist, '')
    Traceback (most recent call last):
    ...
    InvalidEmailAddressError
    >>> registrar.register(mlist, 'some name@example.com')
    Traceback (most recent call last):
    ...
    InvalidEmailAddressError: some name@example.com
    >>> registrar.register(mlist, '<script>@example.com')
    Traceback (most recent call last):
    ...
    InvalidEmailAddressError: <script>@example.com
    >>> registrar.register(mlist, '\xa0@example.com')
    Traceback (most recent call last):
    ...
    InvalidEmailAddressError: \xa0@example.com
    >>> registrar.register(mlist, 'noatsign')
    Traceback (most recent call last):
    ...
    InvalidEmailAddressError: noatsign
    >>> registrar.register(mlist, 'nodom@ain')
    Traceback (most recent call last):
    ...
    InvalidEmailAddressError: nodom@ain


Register an email address
=========================

Registration of an unknown address creates nothing until the confirmation step
is complete.  No ``IUser`` or ``IAddress`` is created at registration time,
but a record is added to the pending database, and the token for that record
is returned.

    >>> token = registrar.register(mlist, 'aperson@example.com', 'Anne Person')
    >>> check_token(token)
    ok

There should be no records in the user manager for this address yet.

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)
    >>> print user_manager.get_user('aperson@example.com')
    None
    >>> print user_manager.get_address('aperson@example.com')
    None

But this address is waiting for confirmation.

    >>> from mailman.interfaces.pending import IPendings
    >>> pendingdb = getUtility(IPendings)

    >>> dump_msgdata(pendingdb.confirm(token, expunge=False))
    delivery_mode: regular
    display_name : Anne Person
    email        : aperson@example.com
    list_name    : alpha@example.com
    type         : registration


Verification by email
=====================

There is also a verification email sitting in the virgin queue now.  This
message is sent to the user in order to verify the registered address.

    >>> from mailman.testing.helpers import get_queue_messages
    >>> items = get_queue_messages('virgin')
    >>> len(items)
    1
    >>> print items[0].msg.as_string()
    MIME-Version: 1.0
    ...
    Subject: confirm ...
    From: alpha-confirm+...@example.com
    To: aperson@example.com
    ...
    <BLANKLINE>
    Email Address Registration Confirmation
    <BLANKLINE>
    Hello, this is the GNU Mailman server at example.com.
    <BLANKLINE>
    We have received a registration request for the email address
    <BLANKLINE>
        aperson@example.com
    <BLANKLINE>
    Before you can start using GNU Mailman at this site, you must first
    confirm that this is your email address.  You can do this by replying to
    this message, keeping the Subject header intact.  Or you can visit this
    web page
    <BLANKLINE>
        http://lists.example.com/confirm/...
    <BLANKLINE>
    If you do not wish to register this email address simply disregard this
    message.  If you think you are being maliciously subscribed to the list,
    or have any other questions, you may contact
    <BLANKLINE>
        postmaster@example.com
    <BLANKLINE>
    >>> dump_msgdata(items[0].msgdata)
    _parsemsg           : False
    listname            : alpha@example.com
    nodecorate          : True
    recipients          : set([u'aperson@example.com'])
    reduced_list_headers: True
    version             : 3

The confirmation token shows up in several places, each of which provides an
easy way for the user to complete the confirmation.  The token will always
appear in a URL in the body of the message.

    >>> sent_token = extract_token(items[0].msg)
    >>> sent_token == token
    True

The same token will appear in the ``From`` header.

    >>> items[0].msg['from'] == 'alpha-confirm+' + token + '@example.com'
    True

It will also appear in the ``Subject`` header.

    >>> items[0].msg['subject'] == 'confirm ' + token
    True

The user would then validate their registered address by clicking on a url or
responding to the message.  Either way, the confirmation process extracts the
token and uses that to confirm the pending registration.

    >>> registrar.confirm(token)
    True

Now, there is an `IAddress` in the database matching the address, as well as
an `IUser` linked to this address.  The `IAddress` is verified.

    >>> found_address = user_manager.get_address('aperson@example.com')
    >>> found_address
    <Address: Anne Person <aperson@example.com> [verified] at ...>
    >>> found_user = user_manager.get_user('aperson@example.com')
    >>> found_user
    <User "Anne Person" (...) at ...>
    >>> found_user.controls(found_address.email)
    True
    >>> from datetime import datetime
    >>> isinstance(found_address.verified_on, datetime)
    True


Non-standard registrations
==========================

If you try to confirm a registration token twice, of course only the first one
will work.  The second one is ignored.

    >>> token = registrar.register(mlist, 'bperson@example.com')
    >>> check_token(token)
    ok
    >>> items = get_queue_messages('virgin')
    >>> len(items)
    1
    >>> sent_token = extract_token(items[0].msg)
    >>> token == sent_token
    True
    >>> registrar.confirm(token)
    True
    >>> registrar.confirm(token)
    False

If an address is in the system, but that address is not linked to a user yet
and the address is not yet validated, then no user is created until the
confirmation step is completed.

    >>> user_manager.create_address('cperson@example.com')
    <Address: cperson@example.com [not verified] at ...>
    >>> token = registrar.register(
    ...     mlist, 'cperson@example.com', 'Claire Person')
    >>> print user_manager.get_user('cperson@example.com')
    None
    >>> items = get_queue_messages('virgin')
    >>> len(items)
    1
    >>> sent_token = extract_token(items[0].msg)
    >>> registrar.confirm(sent_token)
    True
    >>> user_manager.get_user('cperson@example.com')
    <User "Claire Person" (...) at ...>
    >>> user_manager.get_address('cperson@example.com')
    <Address: cperson@example.com [verified] at ...>

Even if the address being registered has already been verified, the
registration sends a confirmation.

    >>> token = registrar.register(mlist, 'cperson@example.com')
    >>> token is not None
    True


Discarding
==========

A confirmation token can also be discarded, say if the user changes his or her
mind about registering.  When discarded, no `IAddress` or `IUser` is created.
::

    >>> token = registrar.register(mlist, 'eperson@example.com', 'Elly Person')
    >>> check_token(token)
    ok
    >>> registrar.discard(token)
    >>> print pendingdb.confirm(token)
    None
    >>> print user_manager.get_address('eperson@example.com')
    None
    >>> print user_manager.get_user('eperson@example.com')
    None

    # Clear the virgin queue of all the preceding confirmation messages.
    >>> ignore = get_queue_messages('virgin')


Registering a new address for an existing user
==============================================

When a new address for an existing user is registered, there isn't too much
different except that the new address will still need to be verified before it
can be used.
::

    >>> from mailman.utilities.datetime import now
    >>> dperson = user_manager.create_user(
    ...     'dperson@example.com', 'Dave Person')
    >>> dperson
    <User "Dave Person" (...) at ...>
    >>> address = user_manager.get_address('dperson@example.com')
    >>> address.verified_on = now()

    >>> from operator import attrgetter
    >>> dump_list(repr(address) for address in dperson.addresses)
    <Address: Dave Person <dperson@example.com> [verified] at ...>
    >>> dperson.register('david.person@example.com', 'David Person')
    <Address: David Person <david.person@example.com> [not verified] at ...>
    >>> token = registrar.register(mlist, 'david.person@example.com')

    >>> items = get_queue_messages('virgin')
    >>> len(items)
    1
    >>> sent_token = extract_token(items[0].msg)
    >>> registrar.confirm(sent_token)
    True
    >>> user = user_manager.get_user('david.person@example.com')
    >>> user is dperson
    True
    >>> user
    <User "Dave Person" (...) at ...>
    >>> dump_list(repr(address) for address in user.addresses)
    <Address: Dave Person <dperson@example.com> [verified] at ...>
    <Address: David Person <david.person@example.com> [verified] at ...>


Corner cases
============

If you try to confirm a token that doesn't exist in the pending database, the
confirm method will just return False.

    >>> registrar.confirm(bytes('no token'))
    False

Likewise, if you try to confirm, through the `IUserRegistrar` interface, a
token that doesn't match a registration event, you will get ``None``.
However, the pending event matched with that token will still be removed.
::

    >>> from mailman.interfaces.pending import IPendable
    >>> from zope.interface import implementer

    >>> @implementer(IPendable)
    ... class SimplePendable(dict):
    ...     pass

    >>> pendable = SimplePendable(type='foo', bar='baz')
    >>> token = pendingdb.add(pendable)
    >>> registrar.confirm(token)
    False
    >>> print pendingdb.confirm(token)
    None


Registration and subscription
=============================

Fred registers with Mailman at the same time that he subscribes to a mailing
list.

    >>> token = registrar.register(
    ...     mlist, 'fred.person@example.com', 'Fred Person')

Before confirmation, Fred is not a member of the mailing list.

    >>> print mlist.members.get_member('fred.person@example.com')
    None

But after confirmation, he is.

    >>> registrar.confirm(token)
    True
    >>> print mlist.members.get_member('fred.person@example.com')
    <Member: Fred Person <fred.person@example.com>
             on alpha@example.com as MemberRole.member>
