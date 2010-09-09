===============
System versions
===============

Mailman system information is available through the ``system`` object, which
implements the ``ISystem`` interface.
::

    >>> from mailman.interfaces.system import ISystem
    >>> from mailman.core.system import system
    >>> from zope.interface.verify import verifyObject

    >>> verifyObject(ISystem, system)
    True

The Mailman version is also available via the ``system`` object.

    >>> print system.mailman_version
    GNU Mailman ...

The Python version running underneath is also available via the ``system``
object.
::

    # The entire python_version string is variable, so this is the best test
    # we can do.
    >>> import sys
    >>> system.python_version == sys.version
    True
