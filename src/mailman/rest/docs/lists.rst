=============
Mailing lists
=============

The REST API can be queried for the set of known mailing lists.  There is a
top level collection that can return all the mailing lists.  There aren't any
yet though.

    >>> dump_json('http://localhost:9001/3.0/lists')
    http_etag: "..."
    start: 0
    total_size: 0

Create a mailing list in a domain and it's accessible via the API.
::

    >>> create_list('test-one@example.com')
    <mailing list "test-one@example.com" at ...>
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/lists')
    entry 0:
        fqdn_listname: test-one@example.com
        http_etag: "..."
        list_name: test-one
        mail_host: example.com
        real_name: Test-one
        self_link: http://localhost:9001/3.0/lists/test-one@example.com
    http_etag: "..."
    start: 0
    total_size: 1

You can also query for lists from a particular domain.
::

    >>> dump_json('http://localhost:9001/3.0/domains/example.com/lists')
    entry 0:
        fqdn_listname: test-one@example.com
        http_etag: "..."
        list_name: test-one
        mail_host: example.com
        real_name: Test-one
        self_link: http://localhost:9001/3.0/lists/test-one@example.com
    http_etag: "..."
    start: 0
    total_size: 1

    >>> dump_json('http://localhost:9001/3.0/domains/no.example.org/lists')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found


Creating lists via the API
==========================

New mailing lists can also be created through the API, by posting to the
``lists`` URL.

    >>> dump_json('http://localhost:9001/3.0/lists', {
    ...           'fqdn_listname': 'test-two@example.com',
    ...           })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/lists/test-two@example.com
    ...

The mailing list exists in the database.
::

    >>> from mailman.interfaces.listmanager import IListManager
    >>> from zope.component import getUtility
    >>> list_manager = getUtility(IListManager)

    >>> list_manager.get('test-two@example.com')
    <mailing list "test-two@example.com" at ...>

    # The above starts a Storm transaction, which will lock the database
    # unless we abort it.
    >>> transaction.abort()

It is also available via the location given in the response.

    >>> dump_json('http://localhost:9001/3.0/lists/test-two@example.com')
    fqdn_listname: test-two@example.com
    http_etag: "..."
    list_name: test-two
    mail_host: example.com
    real_name: Test-two
    self_link: http://localhost:9001/3.0/lists/test-two@example.com

However, you are not allowed to create a mailing list in a domain that does
not exist.

    >>> dump_json('http://localhost:9001/3.0/lists', {
    ...           'fqdn_listname': 'test-three@example.org',
    ...           })
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 400: Domain does not exist example.org

Nor can you create a mailing list that already exists.

    >>> dump_json('http://localhost:9001/3.0/lists', {
    ...           'fqdn_listname': 'test-one@example.com',
    ...           })
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 400: Mailing list exists


Deleting lists via the API
==========================

Existing mailing lists can be deleted through the API, by doing an HTTP
``DELETE`` on the mailing list URL.
::

    >>> dump_json('http://localhost:9001/3.0/lists/test-two@example.com',
    ...           method='DELETE')
    content-length: 0
    date: ...
    server: ...
    status: 204

    # The above starts a Storm transaction, which will lock the database
    # unless we abort it.
    >>> transaction.abort()

The mailing list does not exist.

    >>> print list_manager.get('test-two@example.com')
    None

You cannot delete a mailing list that does not exist or has already been
deleted.
::

    >>> dump_json('http://localhost:9001/3.0/lists/test-two@example.com',
    ...           method='DELETE')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found

    >>> dump_json('http://localhost:9001/3.0/lists/test-ten@example.com',
    ...           method='DELETE')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found
