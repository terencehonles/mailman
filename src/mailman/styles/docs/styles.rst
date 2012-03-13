===========
List styles
===========

List styles are a way to name and apply a template of attribute settings to
new mailing lists.  Every style has a name, which must be unique within the
context of a specific style manager.  There is usually only one global style
manager.

Styles also have a priority, which allows you to specify the order in which
multiple styles will be applied.  A style has a `match` function which is used
to determine whether the style should be applied to a particular mailing list
or not.  And finally, application of a style to a mailing list can really
modify the mailing list any way it wants.

Let's start with a vanilla mailing list and a default style manager.
::

    >>> from mailman.interfaces.listmanager import IListManager
    >>> from zope.component import getUtility
    >>> mlist = getUtility(IListManager).create('_xtest@example.com')

    >>> from mailman.styles.manager import StyleManager
    >>> style_manager = StyleManager()
    >>> style_manager.populate()
    >>> styles = sorted(style.name for style in style_manager.styles)
    >>> len(styles)
    1
    >>> print styles[0]
    default


The default style
=================

There is a default style which implements a legacy style roughly corresponding
to discussion mailing lists.  This style matches when no other styles match,
and it has the lowest priority.  The low priority means that it is matched
last and if it matches, it is applied last.

    >>> default_style = style_manager.get('default')
    >>> print default_style.name
    default
    >>> default_style.priority
    0

Given a mailing list, you can ask the style manager to find all the styles
that match the list.  The registered styles will be sorted by decreasing
priority and each style's ``match()`` method will be called in turn.  The
sorted list of matching styles will be returned -- but not applied -- by the
style manager's ``lookup()`` method.

    >>> matched_styles = [style.name for style in style_manager.lookup(mlist)]
    >>> len(matched_styles)
    1
    >>> print matched_styles[0]
    default


Registering styles
==================

New styles must implement the ``IStyle`` interface.

    >>> from zope.interface import implements
    >>> from mailman.interfaces.styles import IStyle
    >>> class TestStyle:
    ...     implements(IStyle)
    ...     name = 'test'
    ...     priority = 10
    ...     def apply(self, mailing_list):
    ...         # Just does something very simple.
    ...         mailing_list.style_thing = 'thing 1'
    ...     def match(self, mailing_list, styles):
    ...         # Applies to any test list
    ...         if 'test' in mailing_list.fqdn_listname:
    ...             styles.append(self)

You can register a new style with the style manager.

    >>> style_manager.register(TestStyle())

And now if you look up matching styles, you should find only the new test
style.  This is because the default style only gets applied when no other
styles match the mailing list.

    >>> matched_styles = sorted(
    ...     style.name for style in style_manager.lookup(mlist))
    >>> len(matched_styles)
    1
    >>> print matched_styles[0]
    test
    >>> for style in style_manager.lookup(mlist):
    ...     style.apply(mlist)
    >>> print mlist.style_thing
    thing 1


Style priority
==============

When multiple styles match a particular mailing list, they are applied in
descending order of priority.  In other words, a priority zero style would be
applied last.
::

    >>> class AnotherTestStyle(TestStyle):
    ...     name = 'another'
    ...     priority = 5
    ...     # Use the base class's match() method.
    ...     def apply(self, mailing_list):
    ...         mailing_list.style_thing = 'thing 2'

    >>> mlist.style_thing = 'thing 0'
    >>> print mlist.style_thing
    thing 0
    >>> style_manager.register(AnotherTestStyle())
    >>> for style in style_manager.lookup(mlist):
    ...     style.apply(mlist)
    >>> print mlist.style_thing
    thing 2

You can change the priority of a style, and if you reapply the styles, they
will take effect in the new priority order.

    >>> style_1 = style_manager.get('test')
    >>> style_1.priority = 5
    >>> style_2 = style_manager.get('another')
    >>> style_2.priority = 10
    >>> for style in style_manager.lookup(mlist):
    ...     style.apply(mlist)
    >>> print mlist.style_thing
    thing 1


Unregistering styles
====================

You can unregister a style, making it unavailable in the future.

    >>> style_manager.unregister(style_2)
    >>> matched_styles = sorted(
    ...     style.name for style in style_manager.lookup(mlist))
    >>> len(matched_styles)
    1
    >>> print matched_styles[0]
    test
