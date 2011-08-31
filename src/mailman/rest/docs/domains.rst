=======
Domains
=======

`Domains`_ are how Mailman interacts with email host names and web host names.
::

    # The test framework starts out with an example domain, so let's delete
    # that first.
    >>> from mailman.interfaces.domain import IDomainManager
    >>> from zope.component import getUtility
    >>> domain_manager = getUtility(IDomainManager)

    >>> domain_manager.remove('example.com')
    <Domain example.com...>
    >>> transaction.commit()

The REST API can be queried for the set of known domains, of which there are
initially none.

    >>> dump_json('http://localhost:9001/3.0/domains')
    http_etag: "..."
    start: 0
    total_size: 0

Once a domain is added, it is accessible through the API.
::

    >>> domain_manager.add(
    ...     'example.com', 'An example domain', 'http://lists.example.com')
    <Domain example.com, An example domain,
            base_url: http://lists.example.com,
            contact_address: postmaster@example.com>
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/domains')
    entry 0:
        base_url: http://lists.example.com
        contact_address: postmaster@example.com
        description: An example domain
        http_etag: "..."
        mail_host: example.com
        self_link: http://localhost:9001/3.0/domains/example.com
        url_host: lists.example.com
    http_etag: "..."
    start: 0
    total_size: 1

At the top level, all domains are returned as separate entries.
::

    >>> domain_manager.add(
    ...     'example.org',
    ...     base_url='http://mail.example.org',
    ...     contact_address='listmaster@example.org')
    <Domain example.org, base_url: http://mail.example.org,
            contact_address: listmaster@example.org>
    >>> domain_manager.add(
    ...     'lists.example.net',
    ...     'Porkmasters',
    ...     'http://example.net',
    ...     'porkmaster@example.net')
    <Domain lists.example.net, Porkmasters,
            base_url: http://example.net,
            contact_address: porkmaster@example.net>
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/domains')
    entry 0:
        base_url: http://lists.example.com
        contact_address: postmaster@example.com
        description: An example domain
        http_etag: "..."
        mail_host: example.com
        self_link: http://localhost:9001/3.0/domains/example.com
        url_host: lists.example.com
    entry 1:
        base_url: http://mail.example.org
        contact_address: listmaster@example.org
        description: None
        http_etag: "..."
        mail_host: example.org
        self_link: http://localhost:9001/3.0/domains/example.org
        url_host: mail.example.org
    entry 2:
        base_url: http://example.net
        contact_address: porkmaster@example.net
        description: Porkmasters
        http_etag: "..."
        mail_host: lists.example.net
        self_link: http://localhost:9001/3.0/domains/lists.example.net
        url_host: example.net
    http_etag: "..."
    start: 0
    total_size: 3


Individual domains
==================

The information for a single domain is available by following one of the
``self_links`` from the above collection.

    >>> dump_json('http://localhost:9001/3.0/domains/lists.example.net')
    base_url: http://example.net
    contact_address: porkmaster@example.net
    description: Porkmasters
    http_etag: "..."
    mail_host: lists.example.net
    self_link: http://localhost:9001/3.0/domains/lists.example.net
    url_host: example.net

But we get a 404 for a non-existent domain.

    >>> dump_json('http://localhost:9001/3.0/domains/does-not-exist')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found

You can also list all the mailing lists for a given domain.  At first, the
example.com domain does not contain any mailing lists.
::

    >>> dump_json('http://localhost:9001/3.0/domains/example.com/lists')
    http_etag: "..."
    start: 0
    total_size: 0

    >>> dump_json('http://localhost:9001/3.0/lists', {
    ...           'fqdn_listname': 'test-domains@example.com',
    ...           })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/lists/test-domains@example.com
    ...

    >>> dump_json('http://localhost:9001/3.0/domains/example.com/lists')
    entry 0:
        fqdn_listname: test-domains@example.com
        http_etag: "..."
        ...
        self_link: http://localhost:9001/3.0/lists/test-domains@example.com
    http_etag: "..."
    start: 0
    total_size: 1

Other domains continue to contain no mailing lists.

    >>> dump_json('http://localhost:9001/3.0/domains/lists.example.net/lists')
    http_etag: "..."
    start: 0
    total_size: 0


Creating new domains
====================

New domains can be created by posting to the ``domains`` url.

    >>> dump_json('http://localhost:9001/3.0/domains', {
    ...           'mail_host': 'lists.example.com',
    ...           })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/domains/lists.example.com
    ...

Now the web service knows about our new domain.

    >>> dump_json('http://localhost:9001/3.0/domains/lists.example.com')
    base_url: http://lists.example.com
    contact_address: postmaster@lists.example.com
    description: None
    http_etag: "..."
    mail_host: lists.example.com
    self_link: http://localhost:9001/3.0/domains/lists.example.com
    url_host: lists.example.com

And the new domain is in our database.
::

    >>> domain_manager['lists.example.com']
    <Domain lists.example.com,
            base_url: http://lists.example.com,
            contact_address: postmaster@lists.example.com>

    # Unlock the database.
    >>> transaction.abort()

You can also create a new domain with a description, a base url, and a contact
address.
::

    >>> dump_json('http://localhost:9001/3.0/domains', {
    ...           'mail_host': 'my.example.com',
    ...           'description': 'My new domain',
    ...           'base_url': 'http://allmy.example.com',
    ...           'contact_address': 'helpme@example.com'
    ...           })
    content-length: 0
    date: ...
    location: http://localhost:9001/3.0/domains/my.example.com
    ...

    >>> dump_json('http://localhost:9001/3.0/domains/my.example.com')
    base_url: http://allmy.example.com
    contact_address: helpme@example.com
    description: My new domain
    http_etag: "..."
    mail_host: my.example.com
    self_link: http://localhost:9001/3.0/domains/my.example.com
    url_host: allmy.example.com

    >>> domain_manager['my.example.com']
    <Domain my.example.com, My new domain,
            base_url: http://allmy.example.com,
            contact_address: helpme@example.com>

    # Unlock the database.
    >>> transaction.abort()


Deleting domains
================

Domains can also be deleted via the API.

    >>> dump_json('http://localhost:9001/3.0/domains/lists.example.com',
    ...           method='DELETE')
    content-length: 0
    date: ...
    server: ...
    status: 204

It is an error to delete a domain twice.

    >>> dump_json('http://localhost:9001/3.0/domains/lists.example.com',
    ...           method='DELETE')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found


.. _Domains: ../../model/docs/domains.html
