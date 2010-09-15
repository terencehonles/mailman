====================
Implicit destination
====================

The ``implicit-dest`` rule matches when the mailing list's posting address is
not explicitly mentioned in the set of message recipients.

    >>> mlist = create_list('_xtest@example.com')
    >>> rule = config.rules['implicit-dest']
    >>> print rule.name
    implicit-dest

In order to check for implicit destinations, we need to adapt the mailing list
to the appropriate interface.

    >>> from mailman.interfaces.mailinglist import IAcceptableAliasSet
    >>> alias_set = IAcceptableAliasSet(mlist)

This rule matches messages that have an implicit destination, meaning that the
mailing list's posting address isn't included in the explicit recipients.
::

    >>> mlist.require_explicit_destination = True
    >>> alias_set.clear()

    >>> msg = message_from_string("""\
    ... From: aperson@example.org
    ... Subject: An implicit message
    ...
    ... """)
    >>> rule.check(mlist, msg, {})
    True

You can disable implicit destination checks for the mailing list.

    >>> mlist.require_explicit_destination = False
    >>> rule.check(mlist, msg, {})
    False

Even with some recipients, if the posting address is not included, the rule
will match.

    >>> mlist.require_explicit_destination = True
    >>> msg['To'] = 'myfriend@example.com'
    >>> rule.check(mlist, msg, {})
    True

Add the posting address as a recipient and the rule will no longer match.

    >>> msg['Cc'] = '_xtest@example.com'
    >>> rule.check(mlist, msg, {})
    False

Alternatively, if one of the acceptable aliases is in the recipients list,
then the rule will not match.
::

    >>> del msg['cc']
    >>> rule.check(mlist, msg, {})
    True

    >>> alias_set.add('myfriend@example.com')
    >>> rule.check(mlist, msg, {})
    False

A message gated from NNTP will obviously have an implicit destination.  Such
gated messages will not be held for implicit destination because it's assumed
that Mailman pulled it from the appropriate news group.

    >>> rule.check(mlist, msg, dict(from_usenet=True))
    False

Additional aliases can be added.
::

    >>> alias_set.add('other@example.com')
    >>> del msg['to']
    >>> rule.check(mlist, msg, {})
    True

    >>> msg['To'] = 'other@example.com'
    >>> rule.check(mlist, msg, {})
    False

Aliases can be removed.

    >>> alias_set.remove('other@example.com')
    >>> rule.check(mlist, msg, {})
    True

Aliases can also be cleared.
::

    >>> msg['Cc'] = 'myfriend@example.com'
    >>> rule.check(mlist, msg, {})
    False

    >>> alias_set.clear()
    >>> rule.check(mlist, msg, {})
    True


Alias patterns
==============

It's also possible to specify an alias pattern, i.e. a regular expression to
match against the recipients.  For example, we can say that if there is a
recipient in the ``example.net`` domain, then the rule does not match.
::

    >>> alias_set.add('^.*@example.net')
    >>> rule.check(mlist, msg, {})
    True

    >>> msg['To'] = 'you@example.net'
    >>> rule.check(mlist, msg, {})
    False


Bad aliases
===========

You cannot add an alias that looks like neither a pattern nor an email
address.

    >>> alias_set.add('foobar')
    Traceback (most recent call last):
    ...
    ValueError: foobar
