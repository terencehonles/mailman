=====
Users
=====

The REST API can be used to add and remove users, add and remove user
addresses, and change their preferred address, password, or name.  Users are
different than members; the latter represents an email address subscribed to a
specific mailing list.  Users are just people that Mailman knows about.

There are no users yet.

    >>> dump_json('http://localhost:9001/3.0/users')
    http_etag: "..."
    start: 0
    total_size: 0

When there are users in the database, they can be retrieved as a collection.
::

    >>> from zope.component import getUtility
    >>> from mailman.interfaces.usermanager import IUserManager
    >>> user_manager = getUtility(IUserManager)

    >>> anne = user_manager.create_user('anne@example.com', 'Anne Person')
    >>> transaction.commit()
    >>> dump_json('http://localhost:9001/3.0/users')
    entry 0:
        created_on: 2005-08-01T07:49:23
        http_etag: "..."
        real_name: Anne Person
        self_link: http://localhost:9001/3.0/users/1
        user_id: 1
    http_etag: "..."
    start: 0
    total_size: 1

The user ids match.

    >>> json = call_http('http://localhost:9001/3.0/users')
    >>> json['entries'][0]['user_id'] == anne.user_id.int
    True

A user might not have a real name, in which case, the attribute will not be
returned in the REST API.

    >>> dave = user_manager.create_user('dave@example.com')
    >>> transaction.commit()
    >>> dump_json('http://localhost:9001/3.0/users')
    entry 0:
        created_on: 2005-08-01T07:49:23
        http_etag: "..."
        real_name: Anne Person
        self_link: http://localhost:9001/3.0/users/1
        user_id: 1
    entry 1:
        created_on: 2005-08-01T07:49:23
        http_etag: "..."
        self_link: http://localhost:9001/3.0/users/2
        user_id: 2
    http_etag: "..."
    start: 0
    total_size: 2


Creating users via the API
==========================

New users can be created through the REST API.  To do so requires the initial
email address for the user, and optionally the user's full name and password.
::

    >>> transaction.abort()
    >>> dump_json('http://localhost:9001/3.0/users', {
    ...           'email': 'bart@example.com',
    ...           'real_name': 'Bart Person',
    ...           'password': 'bbb',
    ...           })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/users/3
    server: ...
    status: 201

The user exists in the database.
::

    >>> bart = user_manager.get_user('bart@example.com')
    >>> bart
    <User "Bart Person" (3) at ...>

It is also available via the location given in the response.

    >>> dump_json('http://localhost:9001/3.0/users/3')
    created_on: 2005-08-01T07:49:23
    http_etag: "..."
    password: {CLEARTEXT}bbb
    real_name: Bart Person
    self_link: http://localhost:9001/3.0/users/3
    user_id: 3

Because email addresses just have an ``@`` sign in then, there's no confusing
them with user ids.  Thus, a user can be retrieved via its email address.

    >>> dump_json('http://localhost:9001/3.0/users/bart@example.com')
    created_on: 2005-08-01T07:49:23
    http_etag: "..."
    password: {CLEARTEXT}bbb
    real_name: Bart Person
    self_link: http://localhost:9001/3.0/users/3
    user_id: 3

Users can be created without a password.  A *user friendly* password will be
assigned to them automatically, but this password will be encrypted and
therefore cannot be retrieved.  It can be reset though.
::

    >>> transaction.abort()
    >>> dump_json('http://localhost:9001/3.0/users', {
    ...           'email': 'cris@example.com',
    ...           'real_name': 'Cris Person',
    ...           })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/users/4
    server: ...
    status: 201

    >>> dump_json('http://localhost:9001/3.0/users/4')
    created_on: 2005-08-01T07:49:23
    http_etag: "..."
    password: {CLEARTEXT}...
    real_name: Cris Person
    self_link: http://localhost:9001/3.0/users/4
    user_id: 4


Deleting users via the API
==========================

Users can also be deleted via the API.

    >>> dump_json('http://localhost:9001/3.0/users/cris@example.com',
    ...           method='DELETE')
    content-length: 0
    date: ...
    server: ...
    status: 204
    >>> dump_json('http://localhost:9001/3.0/users/cris@example.com')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found


Missing users
=============

It is of course an error to attempt to access a non-existent user, either by
user id...
::

    >>> dump_json('http://localhost:9001/3.0/users/99')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found

...or by email address.
::

    >>> dump_json('http://localhost:9001/3.0/users/zed@example.org')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found


User addresses
==============

Bart may have any number of email addresses associated with their user
account.  We can find out all of these through the API.  The addresses are
sorted in lexical order by original (i.e. case-preserved) email address.
::

    >>> bart.register('bperson@example.com')
    <Address: bperson@example.com [not verified] at ...>
    >>> bart.register('bart.person@example.com')
    <Address: bart.person@example.com [not verified] at ...>
    >>> bart.register('Bart.Q.Person@example.com')
    <Address: Bart.Q.Person@example.com [not verified]
              key: bart.q.person@example.com at ...>
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/users/3/addresses')
    entry 0:
        email: bart.q.person@example.com
        http_etag: "..."
        original_email: Bart.Q.Person@example.com
        registered_on: 2005-08-01T07:49:23
        self_link:
            http://localhost:9001/3.0/addresses/bart.q.person@example.com
    entry 1:
        email: bart.person@example.com
        http_etag: "..."
        original_email: bart.person@example.com
        registered_on: 2005-08-01T07:49:23
        self_link: http://localhost:9001/3.0/addresses/bart.person@example.com
    entry 2:
        email: bart@example.com
        http_etag: "..."
        original_email: bart@example.com
        real_name: Bart Person
        registered_on: 2005-08-01T07:49:23
        self_link: http://localhost:9001/3.0/addresses/bart@example.com
    entry 3:
        email: bperson@example.com
        http_etag: "..."
        original_email: bperson@example.com
        registered_on: 2005-08-01T07:49:23
        self_link: http://localhost:9001/3.0/addresses/bperson@example.com
    http_etag: "..."
    start: 0
    total_size: 4

In fact, any of these addresses can be used to look up Bart's user record.
::

    >>> dump_json('http://localhost:9001/3.0/users/bart@example.com')
    created_on: 2005-08-01T07:49:23
    http_etag: "..."
    password: {CLEARTEXT}bbb
    real_name: Bart Person
    self_link: http://localhost:9001/3.0/users/3
    user_id: 3

    >>> dump_json('http://localhost:9001/3.0/users/bart.person@example.com')
    created_on: 2005-08-01T07:49:23
    http_etag: "..."
    password: {CLEARTEXT}bbb
    real_name: Bart Person
    self_link: http://localhost:9001/3.0/users/3
    user_id: 3

    >>> dump_json('http://localhost:9001/3.0/users/bperson@example.com')
    created_on: 2005-08-01T07:49:23
    http_etag: "..."
    password: {CLEARTEXT}bbb
    real_name: Bart Person
    self_link: http://localhost:9001/3.0/users/3
    user_id: 3

    >>> dump_json('http://localhost:9001/3.0/users/Bart.Q.Person@example.com')
    created_on: 2005-08-01T07:49:23
    http_etag: "..."
    password: {CLEARTEXT}bbb
    real_name: Bart Person
    self_link: http://localhost:9001/3.0/users/3
    user_id: 3
