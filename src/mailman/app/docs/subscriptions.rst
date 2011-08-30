=====================
Subscription services
=====================

The `ISubscriptionService` utility provides higher level convenience methods
useful for searching, retrieving, iterating, adding, and removing
memberships.

    >>> from mailman.interfaces.subscriptions import ISubscriptionService
    >>> from zope.component import getUtility
    >>> service = getUtility(ISubscriptionService)

You can use the service to get all members of all mailing lists, for any
membership role.  At first, there are no memberships.

    >>> service.get_members()
    []
    >>> sum(1 for member in service)
    0
    >>> from uuid import UUID
    >>> print service.get_member(UUID(int=801))
    None


Adding new members
==================

The service can be used to subscribe new members, by default with the `member`
role.  At a minimum, a mailing list and an address for the new user is
required.

    >>> mlist = create_list('test@example.com')
    >>> anne = service.join('test@example.com', 'anne@example.com')
    >>> anne
    <Member: anne <anne@example.com> on test@example.com as MemberRole.member>

The real name of the new member can be given.

    >>> bart = service.join('test@example.com', 'bart@example.com',
    ...                     'Bart Person')
    >>> bart
    <Member: Bart Person <bart@example.com>
             on test@example.com as MemberRole.member>

Other roles can also be subscribed.

    >>> from mailman.interfaces.member import MemberRole
    >>> anne_owner = service.join('test@example.com', 'anne@example.com',
    ...                           role=MemberRole.owner)
    >>> anne_owner
    <Member: anne <anne@example.com> on test@example.com as MemberRole.owner>

And all the subscribed members can now be displayed.

    >>> service.get_members()
    [<Member: anne <anne@example.com> on test@example.com as MemberRole.owner>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.member>,
     <Member: Bart Person <bart@example.com> on test@example.com
              as MemberRole.member>]
    >>> sum(1 for member in service)
    3
    >>> print service.get_member(UUID(int=3))
    <Member: anne <anne@example.com> on test@example.com as MemberRole.owner>

New members can also be added by providing an existing user id instead of an
email address.  However, the user must have a preferred email address.
::

    >>> service.join('test@example.com', bart.user.user_id,
    ...              role=MemberRole.owner)
    Traceback (most recent call last):
    ...
    MissingPreferredAddressError: User must have a preferred address:
        <User "Bart Person" (2) at ...>

    >>> from mailman.utilities.datetime import now
    >>> address = list(bart.user.addresses)[0]
    >>> address.verified_on = now()
    >>> bart.user.preferred_address = address
    >>> service.join('test@example.com', bart.user.user_id,
    ...              role=MemberRole.owner)
    <Member: Bart Person <bart@example.com>
             on test@example.com as MemberRole.owner>


Removing members
================

Regular members can also be removed.

    >>> cris = service.join('test@example.com', 'cris@example.com')
    >>> service.get_members()
    [<Member: anne <anne@example.com> on test@example.com
              as MemberRole.owner>,
     <Member: Bart Person <bart@example.com> on test@example.com
              as MemberRole.owner>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.member>,
     <Member: Bart Person <bart@example.com> on test@example.com
              as MemberRole.member>,
     <Member: cris <cris@example.com> on test@example.com
              as MemberRole.member>]
    >>> sum(1 for member in service)
    5
    >>> service.leave('test@example.com', 'cris@example.com')
    >>> service.get_members()
    [<Member: anne <anne@example.com> on test@example.com
              as MemberRole.owner>,
     <Member: Bart Person <bart@example.com> on test@example.com
              as MemberRole.owner>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.member>,
     <Member: Bart Person <bart@example.com> on test@example.com
              as MemberRole.member>]
    >>> sum(1 for member in service)
    4


Finding members
===============

If you know the member id for a specific member, you can get that member.

    >>> service.get_member(UUID(int=3))
    <Member: anne <anne@example.com> on test@example.com as MemberRole.owner>

If you know the member's address, you can find all their memberships, based on
specific search criteria.  We start by subscribing Anne to a couple of new
mailing lists.

    >>> mlist2 = create_list('foo@example.com')
    >>> mlist3 = create_list('bar@example.com')
    >>> address = list(anne.user.addresses)[0]
    >>> address.verified_on = now()
    >>> anne.user.preferred_address = address
    >>> mlist.subscribe(anne.user, MemberRole.moderator)
    <Member: anne <anne@example.com> on test@example.com
             as MemberRole.moderator>
    >>> mlist2.subscribe(anne.user, MemberRole.member)
    <Member: anne <anne@example.com> on foo@example.com as MemberRole.member>
    >>> mlist3.subscribe(anne.user, MemberRole.owner)
    <Member: anne <anne@example.com> on bar@example.com as MemberRole.owner>

And now we can find all of Anne's memberships.

    >>> service.find_members('anne@example.com')
    [<Member: anne <anne@example.com> on bar@example.com as MemberRole.owner>,
     <Member: anne <anne@example.com> on foo@example.com as MemberRole.member>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.member>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.owner>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.moderator>]

There may be no matching memberships.

    >>> service.find_members('cris@example.com')
    []

Memberships can also be searched for by user id.

    >>> service.find_members(UUID(int=1))
    [<Member: anne <anne@example.com> on bar@example.com as MemberRole.owner>,
     <Member: anne <anne@example.com> on foo@example.com as MemberRole.member>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.member>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.owner>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.moderator>]

You can find all the memberships for a specific mailing list.

    >>> service.find_members(fqdn_listname='test@example.com')
    [<Member: anne <anne@example.com> on test@example.com
              as MemberRole.member>,
     <Member: anne <anne@example.com> on test@example.com as MemberRole.owner>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.moderator>,
     <Member: Bart Person <bart@example.com> on test@example.com
              as MemberRole.member>,
     <Member: Bart Person <bart@example.com> on test@example.com
              as MemberRole.owner>]

You can find all the memberships for an address on a specific mailing list.

    >>> service.find_members('anne@example.com', 'test@example.com')
    [<Member: anne <anne@example.com> on test@example.com
              as MemberRole.member>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.owner>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.moderator>]

You can find all the memberships for an address with a specific role.

    >>> service.find_members('anne@example.com', role=MemberRole.owner)
    [<Member: anne <anne@example.com> on bar@example.com as MemberRole.owner>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.owner>]

You can also find a specific membership by all three criteria.

    >>> service.find_members('anne@example.com', 'test@example.com',
    ...                      MemberRole.owner)
    [<Member: anne <anne@example.com> on test@example.com
              as MemberRole.owner>]
