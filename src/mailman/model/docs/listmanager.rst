========================
The mailing list manager
========================

The ``IListManager`` is how you create, delete, and retrieve mailing list
objects.

    >>> from mailman.interfaces.listmanager import IListManager
    >>> from zope.component import getUtility
    >>> list_manager = getUtility(IListManager)


Creating a mailing list
=======================

Creating the list returns the newly created IMailList object.

    >>> from mailman.interfaces.mailinglist import IMailingList
    >>> mlist = list_manager.create('_xtest@example.com')
    >>> IMailingList.providedBy(mlist)
    True

All lists with identities have a short name, a host name, and a fully
qualified listname.  This latter is what uniquely distinguishes the mailing
list to the system.

    >>> print mlist.list_name
    _xtest
    >>> print mlist.mail_host
    example.com
    >>> print mlist.fqdn_listname
    _xtest@example.com

If you try to create a mailing list with the same name as an existing list,
you will get an exception.

    >>> list_manager.create('_xtest@example.com')
    Traceback (most recent call last):
    ...
    ListAlreadyExistsError: _xtest@example.com

It is an error to create a mailing list that isn't a fully qualified list name
(i.e. posting address).

    >>> list_manager.create('foo')
    Traceback (most recent call last):
    ...
    InvalidEmailAddressError: foo


Deleting a mailing list
=======================

Use the list manager to delete a mailing list.

    >>> list_manager.delete(mlist)
    >>> sorted(list_manager.names)
    []

After deleting the list, you can create it again.

    >>> mlist = list_manager.create('_xtest@example.com')
    >>> print mlist.fqdn_listname
    _xtest@example.com


Retrieving a mailing list
=========================

When a mailing list exists, you can ask the list manager for it and you will
always get the same object back.

    >>> mlist_2 = list_manager.get('_xtest@example.com')
    >>> mlist_2 is mlist
    True

If you try to get a list that doesn't existing yet, you get ``None``.

    >>> print list_manager.get('_xtest_2@example.com')
    None

You also get ``None`` if the list name is invalid.

    >>> print list_manager.get('foo')
    None


Iterating over all mailing lists
================================

Once you've created a bunch of mailing lists, you can use the list manager to
iterate over the mailing list objects, the list posting addresses, or the list
address components.
::

    >>> mlist_3 = list_manager.create('_xtest_3@example.com')
    >>> mlist_4 = list_manager.create('_xtest_4@example.com')

    >>> for name in sorted(list_manager.names):
    ...     print name
    _xtest@example.com
    _xtest_3@example.com
    _xtest_4@example.com

    >>> for fqdn_listname in sorted(m.fqdn_listname
    ...                             for m in list_manager.mailing_lists):
    ...     print fqdn_listname
    _xtest@example.com
    _xtest_3@example.com
    _xtest_4@example.com

    >>> for list_name, mail_host in sorted(list_manager.name_components,
    ...                                    key=lambda (name, host): name):
    ...     print list_name, '@', mail_host
    _xtest   @ example.com
    _xtest_3 @ example.com
    _xtest_4 @ example.com
