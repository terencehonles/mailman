=====
Users
=====

Users are entities that represent people.  A user has a real name and a
optional encoded password.  A user may also have an optional preferences and a
set of addresses they control.  They can even have a *preferred address*,
i.e. one that they use by default.

See `usermanager.txt`_ for examples of how to create, delete, and find users.

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)


User data
=========

Users may have a real name and a password.

    >>> user_1 = user_manager.create_user()
    >>> user_1.password = b'my password'
    >>> user_1.real_name = 'Zoe Person'
    >>> dump_list(user.real_name for user in user_manager.users)
    Zoe Person
    >>> dump_list(user.password for user in user_manager.users)
    my password

The password and real name can be changed at any time.

    >>> user_1.real_name = 'Zoe X. Person'
    >>> user_1.password = b'another password'
    >>> dump_list(user.real_name for user in user_manager.users)
    Zoe X. Person
    >>> dump_list(user.password for user in user_manager.users)
    another password


Basic user identification
=========================

Although rarely visible to users, every user has a unique ID in Mailman, which
never changes.  This ID is generated randomly at the time the user is created,
and is represented by a UUID.

    >>> print user_1.user_id
    00000000-0000-0000-0000-000000000001

The user id cannot change.

    >>> user_1.user_id = 'foo'
    Traceback (most recent call last):
    ...
    AttributeError: can't set attribute

User records also have a date on which they where created.

    # The test suite uses a predictable timestamp.
    >>> print user_1.created_on
    2005-08-01 07:49:23


Users addresses
===============

One of the pieces of information that a user links to is a set of email
addresses they control, in the form of IAddress objects.  A user can control
many addresses, but addresses may be controlled by only one user.

The easiest way to link a user to an address is to just register the new
address on a user object.

    >>> user_1.register('zperson@example.com', 'Zoe Person')
    <Address: Zoe Person <zperson@example.com> [not verified] at 0x...>
    >>> user_1.register('zperson@example.org')
    <Address: zperson@example.org [not verified] at 0x...>
    >>> dump_list(address.email for address in user_1.addresses)
    zperson@example.com
    zperson@example.org
    >>> dump_list(address.real_name for address in user_1.addresses)
    <BLANKLINE>
    Zoe Person

You can also create the address separately and then link it to the user.

    >>> address_1 = user_manager.create_address('zperson@example.net')
    >>> user_1.link(address_1)
    >>> dump_list(address.email for address in user_1.addresses)
    zperson@example.com
    zperson@example.net
    zperson@example.org
    >>> dump_list(address.real_name for address in user_1.addresses)
    <BLANKLINE>
    <BLANKLINE>
    Zoe Person

But don't try to link an address to more than one user.

    >>> another_user = user_manager.create_user()
    >>> another_user.link(address_1)
    Traceback (most recent call last):
    ...
    AddressAlreadyLinkedError: zperson@example.net

You can also ask whether a given user controls a given address.

    >>> user_1.controls(address_1.email)
    True
    >>> user_1.controls('bperson@example.com')
    False

Given a text email address, the user manager can find the user that controls
that address.

    >>> user_manager.get_user('zperson@example.com') is user_1
    True
    >>> user_manager.get_user('zperson@example.net') is user_1
    True
    >>> user_manager.get_user('zperson@example.org') is user_1
    True
    >>> print user_manager.get_user('bperson@example.com')
    None

Addresses can also be unlinked from a user.

    >>> user_1.unlink(address_1)
    >>> user_1.controls('zperson@example.net')
    False
    >>> print user_manager.get_user('aperson@example.net')
    None

But don't try to unlink the address from a user it's not linked to.

    >>> user_1.unlink(address_1)
    Traceback (most recent call last):
    ...
    AddressNotLinkedError: zperson@example.net
    >>> another_user.unlink(address_1)
    Traceback (most recent call last):
    ...
    AddressNotLinkedError: zperson@example.net


Preferred address
=================

Users can register a preferred address.  When subscribing to a mailing list,
unless some other address is explicitly specified, the user will be subscribed
with their preferred address.  This allows them to change their preferred
address once, and have all their subscriptions automatically track this
change.

By default, a user has no preferred address.

    >>> user_2 = user_manager.create_user()
    >>> print user_2.preferred_address
    None

Even when a user registers an address, this address will not be set as the
preferred address.

    >>> anne = user_2.register('anne@example.com', 'Anne Person')
    >>> print user_2.preferred_address
    None

The preferred address must be explicitly registered, however only verified
address may be registered as preferred.

    >>> anne
    <Address: Anne Person <anne@example.com> [not verified] at ...>
    >>> user_2.preferred_address = anne
    Traceback (most recent call last):
    ...
    UnverifiedAddressError: Anne Person <anne@example.com>

Once the address has been verified though, it can be set as the preferred
address, but only if the address is either controlled by the user or
uncontrolled.  In the latter case, setting it as the preferred address makes
it controlled by the user.
::

    >>> from mailman.utilities.datetime import now
    >>> anne.verified_on = now()
    >>> anne
    <Address: Anne Person <anne@example.com> [verified] at ...>
    >>> user_2.controls(anne.email)
    True
    >>> user_2.preferred_address = anne
    >>> user_2.preferred_address
    <Address: Anne Person <anne@example.com> [verified] at ...>

    >>> aperson = user_manager.create_address('aperson@example.com')
    >>> user_2.controls(aperson.email)
    False
    >>> aperson.verified_on = now()
    >>> user_2.preferred_address = aperson
    >>> user_2.controls(aperson.email)
    True

    >>> zperson = list(user_1.addresses)[0]
    >>> zperson.verified_on = now()
    >>> user_2.controls(zperson.email)
    False
    >>> user_1.controls(zperson.email)
    True
    >>> user_2.preferred_address = zperson
    Traceback (most recent call last):
    ...
    AddressAlreadyLinkedError: Zoe Person <zperson@example.com>

A user can disavow their preferred address.

    >>> user_2.preferred_address
    <Address: aperson@example.com [verified] at ...>
    >>> del user_2.preferred_address
    >>> print user_2.preferred_address
    None

The preferred address always shows up in the set of addresses controlled by
this user.

    >>> for address in user_2.addresses:
    ...     print address.email
    anne@example.com
    aperson@example.com


Users and preferences
=====================

This is a helper function for the following section.

    >>> def show_prefs(prefs):
    ...     print 'acknowledge_posts    :', prefs.acknowledge_posts
    ...     print 'preferred_language   :', prefs.preferred_language
    ...     print 'receive_list_copy    :', prefs.receive_list_copy
    ...     print 'receive_own_postings :', prefs.receive_own_postings
    ...     print 'delivery_mode        :', prefs.delivery_mode

Users have preferences, but these preferences have no default settings.

    >>> from mailman.interfaces.preferences import IPreferences
    >>> show_prefs(user_1.preferences)
    acknowledge_posts    : None
    preferred_language   : None
    receive_list_copy    : None
    receive_own_postings : None
    delivery_mode        : None

Some of these preferences are booleans and they can be set to ``True`` or
``False``.
::

    >>> from mailman.interfaces.languages import ILanguageManager
    >>> getUtility(ILanguageManager).add('it', 'iso-8859-1', 'Italian')

    >>> from mailman.core.constants import DeliveryMode
    >>> prefs = user_1.preferences
    >>> prefs.acknowledge_posts = True
    >>> prefs.preferred_language = 'it'
    >>> prefs.receive_list_copy = False
    >>> prefs.receive_own_postings = False
    >>> prefs.delivery_mode = DeliveryMode.regular
    >>> show_prefs(user_1.preferences)
    acknowledge_posts    : True
    preferred_language   : <Language [it] Italian>
    receive_list_copy    : False
    receive_own_postings : False
    delivery_mode        : DeliveryMode.regular


Subscriptions
=============

Users know which mailing lists they are subscribed to, regardless of
membership role.
::

    >>> user_1.link(address_1)
    >>> dump_list(address.email for address in user_1.addresses)
    zperson@example.com
    zperson@example.net
    zperson@example.org
    >>> com = user_manager.get_address('zperson@example.com')
    >>> org = user_manager.get_address('zperson@example.org')
    >>> net = user_manager.get_address('zperson@example.net')

    >>> mlist_1 = create_list('xtest_1@example.com')
    >>> mlist_2 = create_list('xtest_2@example.com')
    >>> mlist_3 = create_list('xtest_3@example.com')
    >>> from mailman.interfaces.member import MemberRole

    >>> mlist_1.subscribe(com, MemberRole.member)
    <Member: Zoe Person <zperson@example.com> on xtest_1@example.com as
        MemberRole.member>
    >>> mlist_2.subscribe(org, MemberRole.member)
    <Member: zperson@example.org on xtest_2@example.com as MemberRole.member>
    >>> mlist_2.subscribe(org, MemberRole.owner)
    <Member: zperson@example.org on xtest_2@example.com as MemberRole.owner>
    >>> mlist_3.subscribe(net, MemberRole.moderator)
    <Member: zperson@example.net on xtest_3@example.com as
        MemberRole.moderator>

    >>> memberships = user_1.memberships
    >>> from mailman.interfaces.roster import IRoster
    >>> from zope.interface.verify import verifyObject
    >>> verifyObject(IRoster, memberships)
    True
    >>> members = sorted(memberships.members)
    >>> len(members)
    4
    >>> def sortkey(member):
    ...     return (member.address.email, member.mailing_list,
    ...             int(member.role))
    >>> for member in sorted(members, key=sortkey):
    ...     print member.address.email, member.mailing_list, member.role
    zperson@example.com xtest_1@example.com MemberRole.member
    zperson@example.net xtest_3@example.com MemberRole.moderator
    zperson@example.org xtest_2@example.com MemberRole.member
    zperson@example.org xtest_2@example.com MemberRole.owner


.. _`usermanager.txt`: usermanager.html
