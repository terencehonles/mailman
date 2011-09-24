====================
Printing the version
====================

You can print the Mailman version number.
::

    >>> from mailman.commands.cli_version import Version
    >>> command = Version()

    >>> command.process(None)
    GNU Mailman 3...
