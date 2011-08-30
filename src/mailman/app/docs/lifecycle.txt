=================================
Application level list life cycle
=================================

The low-level way to create and delete a mailing list is to use the
``IListManager`` interface.  This interface simply adds or removes the
appropriate database entries to record the list's creation.

There is a higher level interface for creating and deleting mailing lists
which performs additional tasks such as:

 * validating the list's posting address (which also serves as the list's
   fully qualified name);
 * ensuring that the list's domain is registered;
 * applying all matching styles to the new list;
 * creating and assigning list owners;
 * notifying watchers of list creation;
 * creating ancillary artifacts (such as the list's on-disk directory)


Posting address validation
==========================

If you try to use the higher-level interface to create a mailing list with a
bogus posting address, you get an exception.

    >>> create_list('not a valid address')
    Traceback (most recent call last):
    ...
    InvalidEmailAddressError: not a valid address

If the posting address is valid, but the domain has not been registered with
Mailman yet, you get an exception.

    >>> create_list('test@example.org')
    Traceback (most recent call last):
    ...
    BadDomainSpecificationError: example.org


Creating a list applies its styles
==================================

Start by registering a test style.
::

    >>> from zope.interface import implements
    >>> from mailman.interfaces.styles import IStyle
    >>> class TestStyle(object):
    ...     implements(IStyle)
    ...     name = 'test'
    ...     priority = 10
    ...     def apply(self, mailing_list):
    ...         # Just does something very simple.
    ...         mailing_list.msg_footer = 'test footer'
    ...     def match(self, mailing_list, styles):
    ...         # Applies to any test list
    ...         if 'test' in mailing_list.fqdn_listname:
    ...             styles.append(self)

    >>> config.style_manager.register(TestStyle())

Using the higher level interface for creating a list, applies all matching
list styles.

    >>> mlist_1 = create_list('test_1@example.com')
    >>> print mlist_1.fqdn_listname
    test_1@example.com
    >>> print mlist_1.msg_footer
    test footer


Creating a list with owners
===========================

You can also specify a list of owner email addresses.  If these addresses are
not yet known, they will be registered, and new users will be linked to them.
However the addresses are not verified.

    >>> owners = [
    ...     'aperson@example.com',
    ...     'bperson@example.com',
    ...     'cperson@example.com',
    ...     'dperson@example.com',
    ...     ]
    >>> mlist_2 = create_list('test_2@example.com', owners)
    >>> print mlist_2.fqdn_listname
    test_2@example.com
    >>> print mlist_2.msg_footer
    test footer
    >>> dump_list(address.email for address in mlist_2.owners.addresses)
    aperson@example.com
    bperson@example.com
    cperson@example.com
    dperson@example.com

None of the owner addresses are verified.

    >>> any(address.verified_on is not None
    ...     for address in mlist_2.owners.addresses)
    False

However, all addresses are linked to users.

    >>> # The owners have no names yet
    >>> len(list(mlist_2.owners.users))
    4

If you create a mailing list with owner addresses that are already known to
the system, they won't be created again.
::

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)

    >>> user_a = user_manager.get_user('aperson@example.com')
    >>> user_b = user_manager.get_user('bperson@example.com')
    >>> user_c = user_manager.get_user('cperson@example.com')
    >>> user_d = user_manager.get_user('dperson@example.com')
    >>> user_a.real_name = 'Anne Person'
    >>> user_b.real_name = 'Bart Person'
    >>> user_c.real_name = 'Caty Person'
    >>> user_d.real_name = 'Dirk Person'

    >>> mlist_3 = create_list('test_3@example.com', owners)
    >>> dump_list(user.real_name for user in mlist_3.owners.users)
    Anne Person
    Bart Person
    Caty Person
    Dirk Person


Deleting a list
===============

Removing a mailing list deletes the list, all its subscribers, and any related
artifacts.
::

    >>> from mailman.app.lifecycle import remove_list
    >>> remove_list(mlist_2.fqdn_listname, mlist_2, True)

    >>> from mailman.interfaces.listmanager import IListManager
    >>> from zope.component import getUtility
    >>> print getUtility(IListManager).get('test_2@example.com')
    None

We should now be able to completely recreate the mailing list.

    >>> mlist_2a = create_list('test_2@example.com', owners)
    >>> dump_list(address.email for address in mlist_2a.owners.addresses)
    aperson@example.com
    bperson@example.com
    cperson@example.com
    dperson@example.com
