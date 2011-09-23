===========
Preferences
===========

Addresses have preferences.
::

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)

    >>> anne = user_manager.create_address('anne@example.com')
    >>> transaction.commit()

Although to start with, an address has no preferences.

    >>> dump_json('http://localhost:9001/3.0/addresses/anne@example.com'
    ...           '/preferences')
    http_etag: "..."
    self_link: http://localhost:9001/3.0/addresses/anne@example.com/preferences

Once the address is given some preferences, they are available through the
REST API.

    >>> anne.preferences.acknowledge_posts = True
    >>> transaction.commit()
    >>> dump_json('http://localhost:9001/3.0/addresses/anne@example.com'
    ...           '/preferences')
    acknowledge_posts: True
    http_etag: "..."
    self_link: http://localhost:9001/3.0/addresses/anne@example.com/preferences

Similarly, users have their own set of preferences, which also start out empty.
::

    >>> bart = user_manager.create_user('bart@example.com')
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/addresses/bart@example.com'
    ...           '/preferences')
    http_etag: "..."
    self_link: http://localhost:9001/3.0/addresses/bart@example.com/preferences

Setting a preference on the user's address does not set them on the user.
::

    >>> list(bart.addresses)[0].preferences.acknowledge_posts = True
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/addresses/bart@example.com'
    ...           '/preferences')
    acknowledge_posts: True
    http_etag: "..."
    self_link: http://localhost:9001/3.0/addresses/bart@example.com/preferences

    >>> dump_json('http://localhost:9001/3.0/users/1/preferences')
    http_etag: "..."
    self_link: http://localhost:9001/3.0/users/1/preferences

Users have their own set of preferences.

    >>> bart.preferences.receive_own_postings = False
    >>> transaction.commit()
    >>> dump_json('http://localhost:9001/3.0/users/1/preferences')
    http_etag: "..."
    receive_own_postings: False
    self_link: http://localhost:9001/3.0/users/1/preferences

Similarly, members have their own separate set of preferences, and just like
the above, setting a preference on the member's address or user does not set
the preference on the member.
::

    >>> from mailman.interfaces.member import MemberRole
    >>> mlist = create_list('test@example.com')
    >>> bart_member = mlist.subscribe(list(bart.addresses)[0])
    >>> bart_member.preferences.receive_list_copy = False
    >>> transaction.commit()
    >>> dump_json('http://localhost:9001/3.0/members/1/preferences')
    http_etag: "..."
    receive_list_copy: False
    self_link: http://localhost:9001/3.0/members/1/preferences


Changing preferences
====================

Preferences for the address, user, or member can be changed through the API.
You can change all the preferences for a particular object by using an HTTP
PUT operation.
::

    >>> dump_json('http://localhost:9001/3.0/addresses/bart@example.com'
    ...           '/preferences', {
    ...           'acknowledge_posts': True,
    ...           'delivery_mode': 'plaintext_digests',
    ...           'delivery_status': 'by_user',
    ...           'preferred_language': 'ja',
    ...           'receive_list_copy': True,
    ...           'receive_own_postings': False,
    ...           }, method='PUT')
    content-length: 0
    date: ...
    server: ...
    status: 204

    >>> dump_json('http://localhost:9001/3.0/addresses/bart@example.com'
    ...           '/preferences')
    acknowledge_posts: True
    delivery_mode: plaintext_digests
    delivery_status: by_user
    http_etag: "..."
    preferred_language: ja
    receive_list_copy: True
    receive_own_postings: False
    self_link: http://localhost:9001/3.0/addresses/bart@example.com/preferences

You can also update just a few of the attributes using PATCH.
::

    >>> dump_json('http://localhost:9001/3.0/addresses/bart@example.com'
    ...           '/preferences', {
    ...           'delivery_mode': 'plaintext_digests',
    ...           'receive_list_copy': False,
    ...           }, method='PATCH')
    content-length: 0
    date: ...
    server: ...
    status: 204

    >>> dump_json('http://localhost:9001/3.0/addresses/bart@example.com'
    ...           '/preferences')
    acknowledge_posts: True
    delivery_mode: plaintext_digests
    delivery_status: by_user
    http_etag: "..."
    preferred_language: ja
    receive_list_copy: False
    receive_own_postings: False
    self_link: http://localhost:9001/3.0/addresses/bart@example.com/preferences


Deleting preferences
====================

Preferences for any of the levels, member, user, or address, can be entirely
deleted.
::

    >>> dump_json('http://localhost:9001/3.0/addresses/anne@example.com'
    ...           '/preferences', {
    ...           'preferred_language': 'ja',
    ...           }, method='PATCH')
    content-length: 0
    date: ...
    server: ...
    status: 204

    >>> dump_json('http://localhost:9001/3.0/addresses/anne@example.com'
    ...           '/preferences')
    acknowledge_posts: True
    http_etag: "5219245d1eea98bc107032013af20ef91bfb5c51"
    preferred_language: ja
    self_link: http://localhost:9001/3.0/addresses/anne@example.com/preferences

    >>> dump_json('http://localhost:9001/3.0/addresses/anne@example.com'
    ...           '/preferences', method='DELETE')
    content-length: 0
    date: ...
    server: ...
    status: 204

    >>> dump_json('http://localhost:9001/3.0/addresses/anne@example.com'
    ...           '/preferences')
    http_etag: "..."
    self_link: http://localhost:9001/3.0/addresses/anne@example.com/preferences


Combined member preferences
===========================

The member resource provides a way to access the set of preference in effect
for a specific subscription.  This stacks the preferences, so that a value is
always available.  The preference value is looked up first on the member,
falling back to the address, then user, then system preference.

Preferences accessed through this interface are always read only.

    >>> dump_json('http://localhost:9001/3.0/members/1/all/preferences')
    acknowledge_posts: True
    delivery_mode: plaintext_digests
    delivery_status: by_user
    http_etag: "..."
    preferred_language: ja
    receive_list_copy: False
    receive_own_postings: False
    self_link: http://localhost:9001/3.0/members/1/all/preferences

These preferences cannot be changed.

    >>> dump_json('http://localhost:9001/3.0/members/1/all/preferences', {
    ...           'delivery_status': 'enabled',
    ...           }, method='PATCH')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 405: 405 Method Not Allowed


System preferences
==================

The Mailman system itself has a default set of preference.  All preference
lookups fall back to these values, which are read-only.

    >>> dump_json('http://localhost:9001/3.0/system/preferences')
    acknowledge_posts: False
    delivery_mode: regular
    delivery_status: enabled
    hide_address: True
    http_etag: "..."
    preferred_language: en
    receive_list_copy: True
    receive_own_postings: True
    self_link: http://localhost:9001/3.0/system/preferences

These preferences cannot be changed.

    >>> dump_json('http://localhost:9001/3.0/system/preferences', {
    ...           'delivery_status': 'enabled',
    ...           }, method='PATCH')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 405: 405 Method Not Allowed
