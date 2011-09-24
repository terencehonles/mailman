===================
Automatic responder
===================

In various situations, Mailman will send an automatic response to the author
of an email message.  For example, if someone sends a command to the
``-request`` address, Mailman will send a response, but to cut down on third
party spam, the sender will only get a certain number of responses per day.

First, given a mailing list you need to adapt it to an ``IAutoResponseSet``.
::

    >>> mlist = create_list('test@example.com')
    >>> from mailman.interfaces.autorespond import IAutoResponseSet
    >>> response_set = IAutoResponseSet(mlist)

    >>> from zope.interface.verify import verifyObject
    >>> verifyObject(IAutoResponseSet, response_set)
    True

You can't adapt other objects to an ``IAutoResponseSet``.

    >>> IAutoResponseSet(object())
    Traceback (most recent call last):
    ...
    TypeError: ('Could not adapt', ...

There are various kinds of response types.  For example, Mailman will send an
automatic response when messages are held for approval, or when it receives an
email command.  You can find out how many responses for a particular address
have already been sent today.
::

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> address = getUtility(IUserManager).create_address(
    ...     'aperson@example.com')

    >>> from mailman.interfaces.autorespond import Response
    >>> response_set.todays_count(address, Response.hold)
    0
    >>> response_set.todays_count(address, Response.command)
    0

Using the response set, we can record that a hold response is sent to the
address.

    >>> response_set.response_sent(address, Response.hold)
    >>> response_set.todays_count(address, Response.hold)
    1
    >>> response_set.todays_count(address, Response.command)
    0

We can also record that a command response was sent.

    >>> response_set.response_sent(address, Response.command)
    >>> response_set.todays_count(address, Response.hold)
    1
    >>> response_set.todays_count(address, Response.command)
    1

Let's send one more.

    >>> response_set.response_sent(address, Response.command)
    >>> response_set.todays_count(address, Response.hold)
    1
    >>> response_set.todays_count(address, Response.command)
    2

Now the day flips over and all the counts reset.
::

    >>> from mailman.utilities.datetime import factory
    >>> factory.fast_forward()

    >>> response_set.todays_count(address, Response.hold)
    0
    >>> response_set.todays_count(address, Response.command)
    0


Response dates
==============

You can also use the response set to get the date of the last response sent.

    >>> response = response_set.last_response(address, Response.hold)
    >>> response.mailing_list
    <mailing list "test@example.com" at ...>
    >>> response.address
    <Address: aperson@example.com [not verified] at ...>
    >>> response.response_type
    <EnumValue: Response.hold [int=1]>
    >>> response.date_sent
    datetime.date(2005, 8, 1)

When another response is sent today, that becomes the last one sent.
::

    >>> response_set.response_sent(address, Response.command)
    >>> response_set.last_response(address, Response.command).date_sent
    datetime.date(2005, 8, 2)

    >>> factory.fast_forward(days=3)
    >>> response_set.response_sent(address, Response.command)
    >>> response_set.last_response(address, Response.command).date_sent
    datetime.date(2005, 8, 5)

If there's been no response sent to a particular address, None is returned.

    >>> address = getUtility(IUserManager).create_address(
    ...     'bperson@example.com')
    >>> response_set.todays_count(address, Response.command)
    0
    >>> print response_set.last_response(address, Response.command)
    None
