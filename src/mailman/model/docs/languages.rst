=========
Languages
=========

Mailman is multilingual.  A language manager handles the known set of
languages at run time, as well as enabling those languages for use in a
running Mailman instance.
::

    >>> from mailman.interfaces.languages import ILanguageManager
    >>> from zope.component import getUtility
    >>> from zope.interface.verify import verifyObject

    >>> mgr = getUtility(ILanguageManager)
    >>> verifyObject(ILanguageManager, mgr)
    True

    # The language manager component comes pre-populated; clear it out.
    >>> mgr.clear()

A language manager keeps track of the languages it knows about.

    >>> list(mgr.codes)
    []
    >>> list(mgr.languages)
    []
    

Adding languages
================

Adding a new language requires three pieces of information, the 2-character
language code, the English description of the language, and the character set
used by the language.  The language object is returned.

    >>> mgr.add('en', 'us-ascii', 'English')
    <Language [en] English>
    >>> mgr.add('it', 'iso-8859-1', 'Italian')
    <Language [it] Italian>

And you can get information for all known languages.

    >>> print mgr['en'].description
    English
    >>> print mgr['en'].charset
    us-ascii
    >>> print mgr['it'].description
    Italian
    >>> print mgr['it'].charset
    iso-8859-1


Other iterations
================

You can iterate over all the known language codes.

    >>> mgr.add('pl', 'iso-8859-2', 'Polish')
    <Language [pl] Polish>
    >>> sorted(mgr.codes)
    [u'en', u'it', u'pl']

You can iterate over all the known languages.

    >>> from operator import attrgetter
    >>> languages = sorted((language for language in mgr.languages),
    ...                    key=attrgetter('code'))
    >>> for language in languages:
    ...     print language.code, language.charset, language.description
    en us-ascii English
    it iso-8859-1 Italian
    pl iso-8859-2 Polish

You can ask whether a particular language code is known.

    >>> 'it' in mgr
    True
    >>> 'xx' in mgr
    False

You can get a particular language by its code.

    >>> print mgr['it'].description
    Italian
    >>> print mgr['xx'].code
    Traceback (most recent call last):
    ...
    KeyError: u'xx'
    >>> print mgr.get('it').description
    Italian
    >>> print mgr.get('xx')
    None
    >>> print mgr.get('xx', 'missing')
    missing


Clearing the known languages
============================

The language manager can forget about all the language codes it knows about.
::

    >>> 'en' in mgr
    True

    # Make a copy of the language manager's dictionary, so we can restore it
    # after the test.  Currently the test layer doesn't manage this.
    >>> saved = mgr._languages.copy()

    >>> mgr.clear()
    >>> 'en' in mgr
    False

    # Restore the data.
    >>> mgr._languages = saved
