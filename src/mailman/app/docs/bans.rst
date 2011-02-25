=======================
Banning email addresses
=======================

Email addresses can be banned from ever subscribing, either to a specific
mailing list or globally within the Mailman system.  Both explicit email
addresses and email address patterns can be banned.

Bans are managed through the `Ban Manager`.

    >>> from zope.component import getUtility
    >>> from mailman.interfaces.bans import IBanManager
    >>> ban_manager = getUtility(IBanManager)

At first, no email addresses are banned, either globally...

    >>> ban_manager.is_banned('anne@example.com')
    False

...or for a specific mailing list.

    >>> ban_manager.is_banned('bart@example.com', 'test@example.com')
    False


Specific bans
=============

An email address can be banned from a specific mailing list by adding a ban to
the ban manager.

    >>> ban_manager.ban('cris@example.com', 'test@example.com')
    >>> ban_manager.is_banned('cris@example.com', 'test@example.com')
    True
    >>> ban_manager.is_banned('bart@example.com', 'test@example.com')
    False

However, this is not a global ban.

    >>> ban_manager.is_banned('cris@example.com')
    False


Global bans
===========

An email address can be banned globally, so that it cannot be subscribed to
any mailing list.

    >>> ban_manager.ban('dave@example.com')

Dave is banned from the test mailing list...

    >>> ban_manager.is_banned('dave@example.com', 'test@example.com')
    True

...and the sample mailing list.

    >>> ban_manager.is_banned('dave@example.com', 'sample@example.com')
    True

Dave is also banned globally.

    >>> ban_manager.is_banned('dave@example.com')
    True

Cris however is not banned globally.

    >>> ban_manager.is_banned('cris@example.com')
    False

Even though Cris is not banned globally, we can add a global ban for her.

    >>> ban_manager.ban('cris@example.com')
    >>> ban_manager.is_banned('cris@example.com')
    True

Cris is obviously still banned from specific mailing lists.

    >>> ban_manager.is_banned('cris@example.com', 'test@example.com')
    True
    >>> ban_manager.is_banned('cris@example.com', 'sample@example.com')
    True

We can remove the global ban to once again just ban her address from the test
list.

    >>> ban_manager.unban('cris@example.com')
    >>> ban_manager.is_banned('cris@example.com', 'test@example.com')
    True
    >>> ban_manager.is_banned('cris@example.com', 'sample@example.com')
    False


Regular expression bans
=======================

Entire email address patterns can be banned, both for a specific mailing list
and globally, just as specific addresses can be banned.  Use this for example,
when an entire domain is a spam faucet.  When using a pattern, the email
address must start with a caret (^).

    >>> ban_manager.ban('^.*@example.org', 'test@example.com')

Now, no one from example.org can subscribe to the test list.

    >>> ban_manager.is_banned('elle@example.org', 'test@example.com')
    True
    >>> ban_manager.is_banned('eperson@example.org', 'test@example.com')
    True
    >>> ban_manager.is_banned('elle@example.com', 'test@example.com')
    False

They are not, however banned globally.

    >>> ban_manager.is_banned('elle@example.org', 'sample@example.com')
    False
    >>> ban_manager.is_banned('elle@example.org')
    False

Of course, we can ban everyone from example.org globally too.

    >>> ban_manager.ban('^.*@example.org')
    >>> ban_manager.is_banned('elle@example.org', 'sample@example.com')
    True
    >>> ban_manager.is_banned('elle@example.org')
    True

We can remove the mailing list ban on the pattern, though the global ban will
still be in place.

    >>> ban_manager.unban('^.*@example.org', 'test@example.com')
    >>> ban_manager.is_banned('elle@example.org', 'test@example.com')
    True
    >>> ban_manager.is_banned('elle@example.org', 'sample@example.com')
    True
    >>> ban_manager.is_banned('elle@example.org')
    True

But once the global ban is removed, everyone from example.org can subscribe to
the mailing lists.

    >>> ban_manager.unban('^.*@example.org')
    >>> ban_manager.is_banned('elle@example.org', 'test@example.com')
    False
    >>> ban_manager.is_banned('elle@example.org', 'sample@example.com')
    False
    >>> ban_manager.is_banned('elle@example.org')
    False


Adding and removing bans
========================

It is not an error to add a ban more than once.  These are just ignored.

    >>> ban_manager.ban('fred@example.com', 'test@example.com')
    >>> ban_manager.ban('fred@example.com', 'test@example.com')
    >>> ban_manager.is_banned('fred@example.com', 'test@example.com')
    True

Nor is it an error to remove a ban more than once.

    >>> ban_manager.unban('fred@example.com', 'test@example.com')
    >>> ban_manager.unban('fred@example.com', 'test@example.com')
    >>> ban_manager.is_banned('fred@example.com', 'test@example.com')
    False
