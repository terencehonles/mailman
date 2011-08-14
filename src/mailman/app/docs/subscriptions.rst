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
    >>> print service.get_member(801)
    None

The service can be used to subscribe new members, but only with the `member`
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

Other roles can be subscribed using the more traditional interfaces.

    >>> from mailman.interfaces.member import MemberRole
    >>> from mailman.utilities.datetime import now
    >>> address = list(anne.user.addresses)[0]
    >>> address.verified_on = now()
    >>> anne.user.preferred_address = address
    >>> anne_owner = mlist.subscribe(anne.user, MemberRole.owner)

And all the subscribed members can now be displayed.

    >>> service.get_members()
    [<Member: anne <anne@example.com> on test@example.com as MemberRole.owner>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.member>,
     <Member: Bart Person <bart@example.com> on test@example.com
              as MemberRole.member>]
    >>> sum(1 for member in service)
    3
    >>> print service.get_member(3)
    <Member: anne <anne@example.com> on test@example.com as MemberRole.owner>

Regular members can also be removed.

    >>> service.leave('test@example.com', 'anne@example.com')
    >>> service.get_members()
    [<Member: anne <anne@example.com> on test@example.com as MemberRole.owner>,
     <Member: Bart Person <bart@example.com> on test@example.com
              as MemberRole.member>]
    >>> sum(1 for member in service)
    2


Finding members
===============

If you know the member id for a specific member, you can get that member.

    >>> service.get_member(3)
    <Member: anne <anne@example.com> on test@example.com as MemberRole.owner>

If you know the member's address, you can find all their memberships, based on
specific search criteria.  At a minimum, you need the member's email address.
::

    >>> mlist2 = create_list('foo@example.com')
    >>> mlist3 = create_list('bar@example.com')
    >>> mlist.subscribe(anne.user, MemberRole.member)
    <Member: anne <anne@example.com> on test@example.com as MemberRole.member>
    >>> mlist.subscribe(anne.user, MemberRole.moderator)
    <Member: anne <anne@example.com> on test@example.com
             as MemberRole.moderator>
    >>> mlist2.subscribe(anne.user, MemberRole.member)
    <Member: anne <anne@example.com> on foo@example.com as MemberRole.member>
    >>> mlist3.subscribe(anne.user, MemberRole.owner)
    <Member: anne <anne@example.com> on bar@example.com as MemberRole.owner>

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

    >>> service.find_members(1)
    [<Member: anne <anne@example.com> on bar@example.com as MemberRole.owner>,
     <Member: anne <anne@example.com> on foo@example.com as MemberRole.member>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.member>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.owner>,
     <Member: anne <anne@example.com> on test@example.com
              as MemberRole.moderator>]

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
