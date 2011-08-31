=======
Domains
=======

..  # The test framework starts out with an example domain, so let's delete
    # that first.
    >>> from mailman.interfaces.domain import IDomainManager
    >>> from zope.component import getUtility
    >>> manager = getUtility(IDomainManager)
    >>> manager.remove('example.com')
    <Domain example.com...>

Domains are how Mailman interacts with email host names and web host names.
::

    >>> from operator import attrgetter
    >>> def show_domains():
    ...     if len(manager) == 0:
    ...         print 'no domains'
    ...         return
    ...     for domain in sorted(manager, key=attrgetter('mail_host')):
    ...         print domain

    >>> show_domains()
    no domains

Adding a domain requires some basic information, of which the email host name
is the only required piece.  The other parts are inferred from that.

    >>> manager.add('example.org')
    <Domain example.org, base_url: http://example.org,
            contact_address: postmaster@example.org>
    >>> show_domains()
    <Domain example.org, base_url: http://example.org,
            contact_address: postmaster@example.org>

We can remove domains too.

    >>> manager.remove('example.org')
    <Domain example.org, base_url: http://example.org,
            contact_address: postmaster@example.org>
    >>> show_domains()
    no domains

Sometimes the email host name is different than the base url for hitting the
web interface for the domain.

    >>> manager.add('example.com', base_url='https://mail.example.com')
    <Domain example.com, base_url: https://mail.example.com,
            contact_address: postmaster@example.com>
    >>> show_domains()
    <Domain example.com, base_url: https://mail.example.com,
            contact_address: postmaster@example.com>

Domains can have explicit descriptions and contact addresses.
::

    >>> manager.add(
    ...     'example.net',
    ...     base_url='http://lists.example.net',
    ...     contact_address='postmaster@example.com',
    ...     description='The example domain')
    <Domain example.net, The example domain,
            base_url: http://lists.example.net,
            contact_address: postmaster@example.com>

    >>> show_domains()
    <Domain example.com, base_url: https://mail.example.com,
            contact_address: postmaster@example.com>
    <Domain example.net, The example domain,
            base_url: http://lists.example.net,
            contact_address: postmaster@example.com>

Domains can list all associated mailing lists with the mailing_lists property.
::

    >>> def show_lists(domain):
    ...     mlists = list(domain.mailing_lists)
    ...     for mlist in mlists:
    ...         print mlist
    ...     if len(mlists) == 0:
    ...         print 'no lists'

    >>> net_domain = manager['example.net']
    >>> com_domain = manager['example.com']
    >>> show_lists(net_domain)
    no lists

    >>> create_list('test@example.net')
    <mailing list "test@example.net" at ...>
    >>> transaction.commit()
    >>> show_lists(net_domain)
    <mailing list "test@example.net" at ...>

    >>> show_lists(com_domain)
    no lists

In the global domain manager, domains are indexed by their email host name.
::

    >>> for domain in sorted(manager, key=attrgetter('mail_host')):
    ...     print domain.mail_host
    example.com
    example.net

    >>> print manager['example.net']
    <Domain example.net, The example domain,
            base_url: http://lists.example.net,
            contact_address: postmaster@example.com>

    >>> print manager['doesnotexist.com']
    Traceback (most recent call last):
    ...
    KeyError: u'doesnotexist.com'

As with a dictionary, you can also get the domain.  If the domain does not
exist, ``None`` or a default is returned.
::

    >>> print manager.get('example.net')
    <Domain example.net, The example domain,
            base_url: http://lists.example.net,
            contact_address: postmaster@example.com>

    >>> print manager.get('doesnotexist.com')
    None

    >>> print manager.get('doesnotexist.com', 'blahdeblah')
    blahdeblah

Non-existent domains cannot be removed.

    >>> manager.remove('doesnotexist.com')
    Traceback (most recent call last):
    ...
    KeyError: u'doesnotexist.com'


Confirmation tokens
===================

Confirmation tokens can be added to the domain's url to generate the URL to a
page users can use to confirm their subscriptions.

    >>> domain = manager['example.net']
    >>> print domain.confirm_url('abc')
    http://lists.example.net/confirm/abc
