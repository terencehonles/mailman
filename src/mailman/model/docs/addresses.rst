===============
Email addresses
===============

Addresses represent a text email address, along with some meta data about
those addresses, such as their registration date, and whether and when they've
been validated.  Addresses may be linked to the users that Mailman knows
about.  Addresses are subscribed to mailing lists though members.

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> user_manager = getUtility(IUserManager)


Creating addresses
==================

Addresses are created directly through the user manager, which starts out with
no addresses.

    >>> dump_list(address.email for address in user_manager.addresses)
    *Empty*

Creating an unlinked email address is straightforward.

    >>> address_1 = user_manager.create_address('aperson@example.com')
    >>> dump_list(address.email for address in user_manager.addresses)
    aperson@example.com

However, such addresses have no real name.

    >>> print address_1.display_name
    <BLANKLINE>

You can also create an email address object with a real name.

    >>> address_2 = user_manager.create_address(
    ...     'bperson@example.com', 'Ben Person')
    >>> dump_list(address.email for address in user_manager.addresses)
    aperson@example.com
    bperson@example.com
    >>> dump_list(address.display_name for address in user_manager.addresses)
    <BLANKLINE>
    Ben Person

The ``str()`` of the address is the RFC 2822 preferred originator format,
while the ``repr()`` carries more information.

    >>> print str(address_2)
    Ben Person <bperson@example.com>
    >>> print repr(address_2)
    <Address: Ben Person <bperson@example.com> [not verified] at 0x...>

You can assign real names to existing addresses.

    >>> address_1.display_name = 'Anne Person'
    >>> dump_list(address.display_name for address in user_manager.addresses)
    Anne Person
    Ben Person

These addresses are not linked to users, and can be seen by searching the user
manager for an associated user.

    >>> print user_manager.get_user('aperson@example.com')
    None
    >>> print user_manager.get_user('bperson@example.com')
    None

You can create email addresses that are linked to users by using a different
interface.

    >>> user_1 = user_manager.create_user(
    ...     'cperson@example.com', u'Claire Person')
    >>> dump_list(address.email for address in user_1.addresses)
    cperson@example.com
    >>> dump_list(address.email for address in user_manager.addresses)
    aperson@example.com
    bperson@example.com
    cperson@example.com
    >>> dump_list(address.display_name for address in user_manager.addresses)
    Anne Person
    Ben Person
    Claire Person

And now you can find the associated user.

    >>> print user_manager.get_user('aperson@example.com')
    None
    >>> print user_manager.get_user('bperson@example.com')
    None
    >>> user_manager.get_user('cperson@example.com')
    <User "Claire Person" (...) at ...>


Deleting addresses
==================

You can remove an unlinked address from the user manager.

    >>> user_manager.delete_address(address_1)
    >>> dump_list(address.email for address in user_manager.addresses)
    bperson@example.com
    cperson@example.com
    >>> dump_list(address.display_name for address in user_manager.addresses)
    Ben Person
    Claire Person

Deleting a linked address does not delete the user, but it does unlink the
address from the user.

    >>> dump_list(address.email for address in user_1.addresses)
    cperson@example.com
    >>> user_1.controls('cperson@example.com')
    True
    >>> address_3 = list(user_1.addresses)[0]
    >>> user_manager.delete_address(address_3)
    >>> dump_list(address.email for address in user_1.addresses)
    *Empty*
    >>> user_1.controls('cperson@example.com')
    False
    >>> dump_list(address.email for address in user_manager.addresses)
    bperson@example.com


Registration and verification
=============================

Addresses have two dates, the date the address was registered on and the date
the address was validated on.  The former is set when the address is created,
but the latter must be set explicitly.

    >>> address_4 = user_manager.create_address(
    ...     'dperson@example.com', 'Dan Person')
    >>> print address_4.registered_on
    2005-08-01 07:49:23
    >>> print address_4.verified_on
    None

The verification date records when the user has completed a mail-back
verification procedure.  It takes a datetime object.

    >>> from mailman.utilities.datetime import now
    >>> address_4.verified_on = now()
    >>> print address_4.verified_on
    2005-08-01 07:49:23

The address shows the verified status in its representation.

    >>> address_4
    <Address: Dan Person <dperson@example.com> [verified] at ...>

An event is triggered when the address gets verified.

    >>> saved_event = None
    >>> address_5 = user_manager.create_address(
    ...     'eperson@example.com', 'Elle Person')
    >>> def save_event(event):
    ...     global saved_event
    ...     saved_event = event
    >>> from mailman.testing.helpers import event_subscribers
    >>> with event_subscribers(save_event):
    ...     address_5.verified_on = now()
    >>> print saved_event
    <AddressVerificationEvent eperson@example.com 2005-08-01 07:49:23>

An event is also triggered when the address is unverified.  In this case,
check the event's address's `verified_on` attribute; if this is None, then the
address is being unverified.

    >>> with event_subscribers(save_event):
    ...     address_5.verified_on = None
    >>> print saved_event
    <AddressVerificationEvent eperson@example.com unverified>
    >>> print saved_event.address.verified_on
    None


Case-preserved addresses
========================

Technically speaking, email addresses are case sensitive in the local part.
Mailman preserves the case of addresses and uses the case preserved version
when sending the user a message, but it treats addresses that are different in
case equivalently in all other situations.

    >>> address_6 = user_manager.create_address(
    ...     'FPERSON@example.com', 'Frank Person')

The str() of such an address prints the RFC 2822 preferred originator format
with the original case-preserved address.  The repr() contains all the gory
details.

    >>> print str(address_6)
    Frank Person <FPERSON@example.com>
    >>> print repr(address_6)
    <Address: Frank Person <FPERSON@example.com> [not verified]
              key: fperson@example.com at 0x...>

Both the case-insensitive version of the address and the original
case-preserved version are available on attributes of the `IAddress` object.

    >>> print address_6.email
    fperson@example.com
    >>> print address_6.original_email
    FPERSON@example.com

Because addresses are case-insensitive for all other purposes, you cannot
create an address that differs only in case.

    >>> user_manager.create_address('fperson@example.com')
    Traceback (most recent call last):
    ...
    ExistingAddressError: FPERSON@example.com
    >>> user_manager.create_address('fperson@EXAMPLE.COM')
    Traceback (most recent call last):
    ...
    ExistingAddressError: FPERSON@example.com
    >>> user_manager.create_address('FPERSON@example.com')
    Traceback (most recent call last):
    ...
    ExistingAddressError: FPERSON@example.com

You can get the address using either the lower cased version or case-preserved
version.  In fact, searching for an address is case insensitive.

    >>> print user_manager.get_address('fperson@example.com').email
    fperson@example.com
    >>> print user_manager.get_address('FPERSON@example.com').email
    fperson@example.com
