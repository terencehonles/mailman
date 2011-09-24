=====
Rules
=====

Rules are applied to each message as part of a rule chain.  Individual rules
simply return a boolean specifying whether the rule matches or not.  Chain
links determine what happens when a rule matches.


All rules
=========

Rules are maintained in the configuration object as a dictionary mapping rule
names to rule objects.

    >>> from zope.interface.verify import verifyObject
    >>> from mailman.interfaces.rules import IRule
    >>> for rule_name in sorted(config.rules):
    ...     rule = config.rules[rule_name]
    ...     print rule_name, verifyObject(IRule, rule)
    administrivia True
    any True
    approved True
    emergency True
    implicit-dest True
    loop True
    max-recipients True
    max-size True
    member-moderation True
    news-moderation True
    no-subject True
    nonmember-moderation True
    suspicious-header True
    truth True

You can get a rule by name.

    >>> rule = config.rules['emergency']
    >>> verifyObject(IRule, rule)
    True


Rule checks
===========

Individual rules can be checked to see if they match, by running the rule's
``check()`` method.  This returns a boolean indicating whether the rule was
matched or not.

    >>> mlist = create_list('_xtest@example.com')
    >>> msg = message_from_string("""\
    ... From: aperson@example.com
    ...
    ... An important message.
    ... """)

For example, the ``emergency`` rule just checks to see if the emergency flag
is set on the mailing list, and the message has not been pre-approved by the
list administrator.

    >>> print rule.name
    emergency
    >>> mlist.emergency = False
    >>> rule.check(mlist, msg, {})
    False
    >>> mlist.emergency = True
    >>> rule.check(mlist, msg, {})
    True
    >>> rule.check(mlist, msg, dict(moderator_approved=True))
    False
