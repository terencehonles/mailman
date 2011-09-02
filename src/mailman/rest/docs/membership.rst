==========
Membership
==========

The REST API can be used to subscribe and unsubscribe users to mailing lists.
A subscribed user is called a *member*.  There is a top level collection that
returns all the members of all known mailing lists.

There are no mailing lists and no members yet.

    >>> dump_json('http://localhost:9001/3.0/members')
    http_etag: "..."
    start: 0
    total_size: 0

We create a mailing list, which starts out with no members.
::

    >>> bee = create_list('bee@example.com')
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/members')
    http_etag: "..."
    start: 0
    total_size: 0


Subscribers
===========

After Bart subscribes to the mailing list, his subscription is available via
the REST interface.
::

    >>> from mailman.interfaces.member import MemberRole
    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)

    >>> from mailman.testing.helpers import subscribe
    >>> subscribe(bee, 'Bart')
    >>> dump_json('http://localhost:9001/3.0/members')
    entry 0:
        address: bperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/1
        user: http://localhost:9001/3.0/users/1
    http_etag: "..."
    start: 0
    total_size: 1

Bart's specific membership can be accessed directly:

    >>> dump_json('http://localhost:9001/3.0/members/1')
    address: bperson@example.com
    delivery_mode: regular
    fqdn_listname: bee@example.com
    http_etag: ...
    role: member
    self_link: http://localhost:9001/3.0/members/1
    user: http://localhost:9001/3.0/users/1

When Cris also joins the mailing list, her subscription is also available via
the REST interface.

    >>> subscribe(bee, 'Cris')
    >>> dump_json('http://localhost:9001/3.0/members')
    entry 0:
        address: bperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/1
        user: http://localhost:9001/3.0/users/1
    entry 1:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/2
        user: http://localhost:9001/3.0/users/2
    http_etag: "..."
    start: 0
    total_size: 2

The subscribed members are returned in alphabetical order, so when Anna
subscribes, she is returned first.
::

    >>> subscribe(bee, 'Anna')

    >>> dump_json('http://localhost:9001/3.0/members')
    entry 0:
        address: aperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/3
        user: http://localhost:9001/3.0/users/3
    entry 1:
        address: bperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/1
        user: http://localhost:9001/3.0/users/1
    entry 2:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/2
        user: http://localhost:9001/3.0/users/2
    http_etag: "..."
    start: 0
    total_size: 3

Subscriptions are also returned alphabetically by mailing list posting
address.  Anna and Cris subscribe to this new mailing list.
::

    >>> ant = create_list('ant@example.com')
    >>> subscribe(ant, 'Anna')
    >>> subscribe(ant, 'Cris')

User ids are different than member ids.

    >>> dump_json('http://localhost:9001/3.0/members')
    entry 0:
        address: aperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/4
        user: http://localhost:9001/3.0/users/3
    entry 1:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/5
        user: http://localhost:9001/3.0/users/2
    entry 2:
        address: aperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/3
        user: http://localhost:9001/3.0/users/3
    entry 3:
        address: bperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/1
        user: http://localhost:9001/3.0/users/1
    entry 4:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/2
        user: http://localhost:9001/3.0/users/2
    http_etag: "..."
    start: 0
    total_size: 5

We can also get just the members of a single mailing list.

    >>> dump_json(
    ...     'http://localhost:9001/3.0/lists/ant@example.com/roster/member')
    entry 0:
        address: aperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/4
        user: http://localhost:9001/3.0/users/3
    entry 1:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/5
        user: http://localhost:9001/3.0/users/2
    http_etag: ...
    start: 0
    total_size: 2


Owners and moderators
=====================

Mailing list owners and moderators also show up in the REST API.  Cris becomes
an owner of the `ant` mailing list and Dave becomes a moderator of the `bee`
mailing list.
::

    >>> dump_json('http://localhost:9001/3.0/members', {
    ...           'fqdn_listname': 'ant@example.com',
    ...           'subscriber': 'dperson@example.com',
    ...           'role': 'moderator',
    ...           })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/members/6
    server: ...
    status: 201

    >>> dump_json('http://localhost:9001/3.0/members', {
    ...           'fqdn_listname': 'bee@example.com',
    ...           'subscriber': 'cperson@example.com',
    ...           'role': 'owner',
    ...           })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/members/7
    server: ...
    status: 201

    >>> dump_json('http://localhost:9001/3.0/members')
    entry 0:
        address: dperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: ...
        role: moderator
        self_link: http://localhost:9001/3.0/members/6
        user: http://localhost:9001/3.0/users/4
    entry 1:
        address: aperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/4
        user: http://localhost:9001/3.0/users/3
    entry 2:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/5
        user: http://localhost:9001/3.0/users/2
    entry 3:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: owner
        self_link: http://localhost:9001/3.0/members/7
        user: http://localhost:9001/3.0/users/2
    entry 4:
        address: aperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/3
        user: http://localhost:9001/3.0/users/3
    entry 5:
        address: bperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/1
        user: http://localhost:9001/3.0/users/1
    entry 6:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/2
        user: http://localhost:9001/3.0/users/2
    http_etag: "..."
    start: 0
    total_size: 7

We can access all the owners of a list.

    >>> dump_json(
    ...     'http://localhost:9001/3.0/lists/bee@example.com/roster/owner')
    entry 0:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: owner
        self_link: http://localhost:9001/3.0/members/7
        user: http://localhost:9001/3.0/users/2
    http_etag: ...
    start: 0
    total_size: 1


Finding members
===============

A specific member can always be referenced by their role and address.

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'bee@example.com/owner/cperson@example.com')
    address: cperson@example.com
    delivery_mode: regular
    fqdn_listname: bee@example.com
    http_etag: ...
    role: owner
    self_link: http://localhost:9001/3.0/members/7
    user: http://localhost:9001/3.0/users/2

You can find a specific member based on several different criteria.  For
example, we can search for all the memberships of a particular address.

    >>> dump_json('http://localhost:9001/3.0/members/find', {
    ...           'subscriber': 'aperson@example.com',
    ...           })
    entry 0:
        address: aperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/4
        user: http://localhost:9001/3.0/users/3
    entry 1:
        address: aperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/3
        user: http://localhost:9001/3.0/users/3
    http_etag: ...
    start: 0
    total_size: 2

Or, we can find all the memberships for a particular mailing list.

    >>> dump_json('http://localhost:9001/3.0/members/find', {
    ...           'fqdn_listname': 'bee@example.com',
    ...           })
    entry 0:
        address: aperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/3
        user: http://localhost:9001/3.0/users/3
    entry 1:
        address: bperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/1
        user: http://localhost:9001/3.0/users/1
    entry 2:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/2
        user: http://localhost:9001/3.0/users/2
    entry 3:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: owner
        self_link: http://localhost:9001/3.0/members/7
        user: http://localhost:9001/3.0/users/2
    http_etag: "..."
    start: 0
    total_size: 4

Or, we can find all the memberships for an address on a particular mailing
list.

    >>> dump_json('http://localhost:9001/3.0/members/find', {
    ...           'subscriber': 'cperson@example.com',
    ...           'fqdn_listname': 'bee@example.com',
    ...           })
    entry 0:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/2
        user: http://localhost:9001/3.0/users/2
    entry 1:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: owner
        self_link: http://localhost:9001/3.0/members/7
        user: http://localhost:9001/3.0/users/2
    http_etag: ...
    start: 0
    total_size: 2

Or, we can find all the memberships for an address with a specific role.

    >>> dump_json('http://localhost:9001/3.0/members/find', {
    ...           'subscriber': 'cperson@example.com',
    ...           'role': 'member',
    ...           })
    entry 0:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/5
        user: http://localhost:9001/3.0/users/2
    entry 1:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/2
        user: http://localhost:9001/3.0/users/2
    http_etag: ...
    start: 0
    total_size: 2

Finally, we can search for a specific member given all three criteria.

    >>> dump_json('http://localhost:9001/3.0/members/find', {
    ...           'subscriber': 'cperson@example.com',
    ...           'fqdn_listname': 'bee@example.com',
    ...           'role': 'member',
    ...           })
    entry 0:
        address: cperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/2
        user: http://localhost:9001/3.0/users/2
    http_etag: ...
    start: 0
    total_size: 1


Joining a mailing list
======================

A user can be subscribed to a mailing list via the REST API, either by a
specific address, or more generally by their preferred address.  A subscribed
user is called a member.

Elly wants to subscribes to the `ant` mailing list.  Since Elly's email
address is not yet known to Mailman, a user is created for her.  By default,
get gets a regular delivery.

    >>> dump_json('http://localhost:9001/3.0/members', {
    ...           'fqdn_listname': 'ant@example.com',
    ...           'subscriber': 'eperson@example.com',
    ...           'real_name': 'Elly Person',
    ...           })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/members/8
    server: ...
    status: 201

Elly is now a known user, and a member of the mailing list.
::

    >>> elly = user_manager.get_user('eperson@example.com')
    >>> elly
    <User "Elly Person" (...) at ...>

    >>> set(member.mailing_list for member in elly.memberships.members)
    set([u'ant@example.com'])

    >>> dump_json('http://localhost:9001/3.0/members')
    entry 0:
    ...
    entry 3:
        address: eperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: ...
        role: member
        self_link: http://localhost:9001/3.0/members/8
        user: http://localhost:9001/3.0/users/5
    ...

Gwen is a user with a preferred address.  She subscribes to the `ant` mailing
list with her preferred address.
::

    >>> from mailman.utilities.datetime import now
    >>> gwen = user_manager.create_user('gwen@example.com', 'Gwen Person')
    >>> preferred = list(gwen.addresses)[0]
    >>> preferred.verified_on = now()
    >>> gwen.preferred_address = preferred

    # Note that we must extract the user id before we commit the transaction.
    # This is because accessing the .user_id attribute will lock the database
    # in the testing process, breaking the REST queue process.  Also, the
    # user_id is a UUID internally, but an integer (represented as a string)
    # is required by the REST API.
    >>> user_id = gwen.user_id.int
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/members', {
    ...     'fqdn_listname': 'ant@example.com',
    ...     'subscriber': user_id,
    ...     })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/members/9
    server: ...
    status: 201

    >>> dump_json('http://localhost:9001/3.0/members')
    entry 0:
    ...
    entry 4:
        address: gwen@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: "..."
        role: member
        self_link: http://localhost:9001/3.0/members/9
        user: http://localhost:9001/3.0/users/6
    ...
    total_size: 9

When Gwen changes her preferred address, her subscription automatically tracks
the new address.
::

    >>> new_preferred = gwen.register('gwen.person@example.com')
    >>> new_preferred.verified_on = now()
    >>> gwen.preferred_address = new_preferred
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/members')
    entry 0:
    ...
    entry 4:
        address: gwen.person@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: "..."
        role: member
        self_link: http://localhost:9001/3.0/members/9
        user: http://localhost:9001/3.0/users/6
    ...
    total_size: 9


Leaving a mailing list
======================

Elly decides she does not want to be a member of the mailing list after all,
so she leaves from the mailing list.
::

    # Ensure our previous reads don't keep the database lock.
    >>> transaction.abort()
    >>> dump_json('http://localhost:9001/3.0/members/8',
    ...           method='DELETE')
    content-length: 0
    ...
    status: 204

Elly is no longer a member of the mailing list.

    >>> set(member.mailing_list for member in elly.memberships.members)
    set([])


Digest delivery
===============

Fred joins the `ant` mailing list but wants MIME digest delivery.
::

    >>> transaction.abort()
    >>> dump_json('http://localhost:9001/3.0/members', {
    ...           'fqdn_listname': 'ant@example.com',
    ...           'subscriber': 'fperson@example.com',
    ...           'real_name': 'Fred Person',
    ...           'delivery_mode': 'mime_digests',
    ...           })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/members/10
    server: ...
    status: 201

    >>> fred = user_manager.get_user('fperson@example.com')
    >>> memberships = list(fred.memberships.members)
    >>> len(memberships)
    1

Fred is getting MIME deliveries.

    >>> memberships[0]
    <Member: Fred Person <fperson@example.com>
             on ant@example.com as MemberRole.member>
    >>> print memberships[0].delivery_mode
    DeliveryMode.mime_digests

    >>> dump_json('http://localhost:9001/3.0/members/10')
    address: fperson@example.com
    delivery_mode: mime_digests
    fqdn_listname: ant@example.com
    http_etag: "..."
    role: member
    self_link: http://localhost:9001/3.0/members/10
    user: http://localhost:9001/3.0/users/7

Fred wants to change his delivery from MIME digest back to regular delivery.
This can be done by PATCH'ing his member with the `delivery_mode` parameter.
::

    >>> transaction.abort()
    >>> dump_json('http://localhost:9001/3.0/members/10', {
    ...           'delivery_mode': 'regular',
    ...           }, method='PATCH')
    content-length: 0
    date: ...
    server: ...
    status: 204

    >>> dump_json('http://localhost:9001/3.0/members/10')
    address: fperson@example.com
    delivery_mode: regular
    fqdn_listname: ant@example.com
    http_etag: "..."
    role: member
    self_link: http://localhost:9001/3.0/members/10
    user: http://localhost:9001/3.0/users/7

If a PATCH request changes no attributes, nothing happens.
::

    >>> dump_json('http://localhost:9001/3.0/members/10', method='PATCH')
    content-length: 0
    date: ...
    server: ...
    status: 204

    >>> dump_json('http://localhost:9001/3.0/members/10')
    address: fperson@example.com
    delivery_mode: regular
    fqdn_listname: ant@example.com
    http_etag: "..."
    role: member
    self_link: http://localhost:9001/3.0/members/10
    user: http://localhost:9001/3.0/users/7


Changing delivery address
=========================

As shown above, Gwen is subscribed to a mailing list with her preferred email
address.  If she changes her preferred address, this automatically changes the
address she will receive deliveries at for all such memberships.

However, when Herb subscribes to a couple of mailing lists with explicit
addresses, he must change each subscription explicitly.

Herb controls multiple email addresses.  All of these addresses are verified.

    >>> herb = user_manager.create_user('herb@example.com', 'Herb Person')
    >>> herb_1 = list(herb.addresses)[0]
    >>> herb_2 = herb.register('hperson@example.com')
    >>> herb_3 = herb.register('herb.person@example.com')
    >>> for address in herb.addresses:
    ...     address.verified_on = now()

Herb subscribes to both the `ant` and `bee` mailing lists with one of his
addresses.

    >>> ant.subscribe(herb_1)
    <Member: Herb Person <herb@example.com> on
             ant@example.com as MemberRole.member>
    >>> bee.subscribe(herb_1)
    <Member: Herb Person <herb@example.com> on
             bee@example.com as MemberRole.member>
    >>> transaction.commit()
    >>> dump_json('http://localhost:9001/3.0/members')
    entry 0:
    ...
    entry 5:
        address: herb@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: "..."
        role: member
        self_link: http://localhost:9001/3.0/members/11
        user: http://localhost:9001/3.0/users/8
    ...
    entry 10:
        address: herb@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: "..."
        role: member
        self_link: http://localhost:9001/3.0/members/12
        user: http://localhost:9001/3.0/users/8
    http_etag: "..."
    start: 0
    total_size: 11

In order to change all of his subscriptions to use a different email address,
Herb must iterate through his memberships explicitly.

    >>> from mailman.testing.helpers import call_api
    >>> content, response = call_api('http://localhost:9001/3.0/addresses/'
    ...                              'herb@example.com/memberships')
    >>> memberships = [entry['self_link'] for entry in content['entries']]
    >>> for url in sorted(memberships):
    ...     print url
    http://localhost:9001/3.0/members/11
    http://localhost:9001/3.0/members/12

For each membership resource, the subscription address is changed by PATCH'ing
the `address` attribute.

    >>> dump_json('http://localhost:9001/3.0/members/11', {
    ...           'address': 'hperson@example.com',
    ...           }, method='PATCH')
    content-length: 0
    date: ...
    server: ...
    status: 204

    >>> dump_json('http://localhost:9001/3.0/members/12', {
    ...           'address': 'hperson@example.com',
    ...           }, method='PATCH')
    content-length: 0
    date: ...
    server: ...
    status: 204

Herb's memberships with the old address are gone.

    >>> dump_json('http://localhost:9001/3.0/addresses/'
    ...           'herb@example.com/memberships')
    http_etag: "..."
    start: 0
    total_size: 0

Herb's memberships have been updated with his new email address.  Of course,
his membership ids have not changed.

    >>> dump_json('http://localhost:9001/3.0/addresses/'
    ...           'hperson@example.com/memberships')
    entry 0:
        address: hperson@example.com
        delivery_mode: regular
        fqdn_listname: ant@example.com
        http_etag: "..."
        role: member
        self_link: http://localhost:9001/3.0/members/11
        user: http://localhost:9001/3.0/users/8
    entry 1:
        address: hperson@example.com
        delivery_mode: regular
        fqdn_listname: bee@example.com
        http_etag: "..."
        role: member
        self_link: http://localhost:9001/3.0/members/12
        user: http://localhost:9001/3.0/users/8
    http_etag: "..."
    start: 0
    total_size: 2
