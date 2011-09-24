======================
Mailing list addresses
======================

Every mailing list has a number of addresses which are publicly available.
These are defined in the ``IMailingListAddresses`` interface.

    >>> mlist = create_list('_xtest@example.com')

The posting address is where people send messages to be posted to the mailing
list.  This is exactly the same as the fully qualified list name.

    >>> print mlist.fqdn_listname
    _xtest@example.com
    >>> print mlist.posting_address
    _xtest@example.com

Messages to the mailing list's `no reply` address always get discarded without
prejudice.

    >>> print mlist.no_reply_address
    noreply@example.com

The mailing list's owner address reaches the human moderators.

    >>> print mlist.owner_address
    _xtest-owner@example.com

The request address goes to the list's email command robot.

    >>> print mlist.request_address
    _xtest-request@example.com

The bounces address accepts and processes all potential bounces.

    >>> print mlist.bounces_address
    _xtest-bounces@example.com

The join (a.k.a. subscribe) address is where someone can email to get added to
the mailing list.  The subscribe alias is a synonym for join, but it's
deprecated.

    >>> print mlist.join_address
    _xtest-join@example.com
    >>> print mlist.subscribe_address
    _xtest-subscribe@example.com

The leave (a.k.a. unsubscribe) address is where someone can email to get added
to the mailing list.  The unsubscribe alias is a synonym for leave, but it's
deprecated.

    >>> print mlist.leave_address
    _xtest-leave@example.com
    >>> print mlist.unsubscribe_address
    _xtest-unsubscribe@example.com


Email confirmations
===================

Email confirmation messages are sent when actions such as subscriptions need
to be confirmed.  It requires that a cookie be provided, which will be
included in the local part of the email address.  The exact format of this is
dependent on the ``verp_confirm_format`` configuration variable.
::

    >>> print mlist.confirm_address('cookie')
    _xtest-confirm+cookie@example.com
    >>> print mlist.confirm_address('wookie')
    _xtest-confirm+wookie@example.com

    >>> config.push('test config', """
    ... [mta]
    ... verp_confirm_format: $address---$cookie
    ... """)
    >>> print mlist.confirm_address('cookie')
    _xtest-confirm---cookie@example.com
    >>> config.pop('test config')
