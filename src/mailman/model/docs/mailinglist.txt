=============
Mailing lists
=============

.. XXX 2010-06-18 BAW: This documentation needs a lot more detail.

The mailing list is a core object in Mailman.  It is uniquely identified in
the system by its posting address, i.e. the email address you would send a
message to in order to post a message to the mailing list.  This must be fully
qualified.

    >>> mlist = create_list('aardvark@example.com')
    >>> print mlist.fqdn_listname
    aardvark@example.com

The mailing list also has convenient attributes for accessing the list's short
name (i.e. local part) and host name.

    >>> print mlist.list_name
    aardvark
    >>> print mlist.mail_host
    example.com


Rosters
=======

Mailing list membership is represented by `rosters`.  Each mailing list has
several rosters of members, representing the subscribers to the mailing list,
the owners, the moderators, and so on.  The rosters are defined by a
membership role.

Addresses can be explicitly subscribed to a mailing list.  By default, a
subscription puts the address in the `member` role, meaning that address will
receive a copy of any message sent to the mailing list.
::

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)

    >>> aperson = user_manager.create_address('aperson@example.com')
    >>> bperson = user_manager.create_address('bperson@example.com')
    >>> mlist.subscribe(aperson)
    <Member: aperson@example.com on aardvark@example.com as MemberRole.member>
    >>> mlist.subscribe(bperson)
    <Member: bperson@example.com on aardvark@example.com as MemberRole.member>

Both addresses appear on the roster of members.

    >>> for member in mlist.members.members:
    ...     print member
    <Member: aperson@example.com on aardvark@example.com as MemberRole.member>
    <Member: bperson@example.com on aardvark@example.com as MemberRole.member>

By explicitly specifying the role of the subscription, an address can be added
to the owner and moderator rosters.

    >>> from mailman.interfaces.member import MemberRole
    >>> mlist.subscribe(aperson, MemberRole.owner)
    <Member: aperson@example.com on aardvark@example.com as MemberRole.owner>
    >>> cperson = user_manager.create_address('cperson@example.com')
    >>> mlist.subscribe(cperson, MemberRole.owner)
    <Member: cperson@example.com on aardvark@example.com as MemberRole.owner>
    >>> mlist.subscribe(cperson, MemberRole.moderator)
    <Member: cperson@example.com on aardvark@example.com
             as MemberRole.moderator>

A Person is now both a member and an owner of the mailing list.  C Person is
an owner and a moderator.
::

    >>> for member in mlist.owners.members:
    ...     print member
    <Member: aperson@example.com on aardvark@example.com as MemberRole.owner>
    <Member: cperson@example.com on aardvark@example.com as MemberRole.owner>

    >>> for member in mlist.moderators.members:
    ...     print member
    <Member: cperson@example.com on aardvark@example.com
             as MemberRole.moderator>


All rosters can also be accessed indirectly.
::

    >>> roster = mlist.get_roster(MemberRole.member)
    >>> for member in roster.members:
    ...     print member
    <Member: aperson@example.com on aardvark@example.com as MemberRole.member>
    <Member: bperson@example.com on aardvark@example.com as MemberRole.member>

    >>> roster = mlist.get_roster(MemberRole.owner)
    >>> for member in roster.members:
    ...     print member
    <Member: aperson@example.com on aardvark@example.com as MemberRole.owner>
    <Member: cperson@example.com on aardvark@example.com as MemberRole.owner>

    >>> roster = mlist.get_roster(MemberRole.moderator)
    >>> for member in roster.members:
    ...     print member
    <Member: cperson@example.com on aardvark@example.com
             as MemberRole.moderator>


Subscribing users
=================

An alternative way of subscribing to a mailing list is as a user with a
preferred address.  This way the user can change their subscription address
just by changing their preferred address.
::

    >>> from mailman.utilities.datetime import now
    >>> user = user_manager.create_user('dperson@example.com', 'Dave Person')
    >>> address = list(user.addresses)[0]
    >>> address.verified_on = now()
    >>> user.preferred_address = address

    >>> mlist.subscribe(user)
    <Member: Dave Person <dperson@example.com> on aardvark@example.com
             as MemberRole.member>
    >>> for member in mlist.members.members:
    ...     print member
    <Member: aperson@example.com on aardvark@example.com as MemberRole.member>
    <Member: bperson@example.com on aardvark@example.com as MemberRole.member>
    <Member: Dave Person <dperson@example.com> on aardvark@example.com
             as MemberRole.member>

    >>> new_address = user.register('dave.person@example.com')
    >>> new_address.verified_on = now()
    >>> user.preferred_address = new_address

    >>> for member in mlist.members.members:
    ...     print member
    <Member: aperson@example.com on aardvark@example.com as MemberRole.member>
    <Member: bperson@example.com on aardvark@example.com as MemberRole.member>
    <Member: dave.person@example.com on aardvark@example.com
             as MemberRole.member>

A user is not allowed to subscribe more than once to the mailing list.

    >>> mlist.subscribe(user)
    Traceback (most recent call last):
    ...
    AlreadySubscribedError: <User "Dave Person" (1) at ...>
    is already a MemberRole.member of mailing list aardvark@example.com

However, they are allowed to subscribe again with a specific address, even if
this address is their preferred address.

    >>> mlist.subscribe(user.preferred_address)
    <Member: dave.person@example.com
             on aardvark@example.com as MemberRole.member>

A user cannot subscribe to a mailing list without a preferred address.

    >>> user = user_manager.create_user('eperson@example.com', 'Elly Person')
    >>> address = list(user.addresses)[0]
    >>> address.verified_on = now()
    >>> mlist.subscribe(user)
    Traceback (most recent call last):
    ...
    MissingPreferredAddressError: User must have a preferred address:
    <User "Elly Person" (2) at ...>
