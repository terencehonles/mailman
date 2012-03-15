===================
Importing list data
===================

If you have the config.pck file for a version 2.1 mailing list, you can import
that into an existing mailing list in Mailman 3.0.
::

    >>> from mailman.commands.cli_import import Import21
    >>> command = Import21()

    >>> class FakeArgs:
    ...     listname = None
    ...     pickle_file = None

    >>> class FakeParser:
    ...     def error(self, message):
    ...         print message
    >>> command.parser = FakeParser()

You must specify the mailing list you are importing into, and it must exist.
::

    >>> command.process(FakeArgs)
    List name is required

    >>> FakeArgs.listname = ['import@example.com']
    >>> command.process(FakeArgs)
    No such list: import@example.com

When the mailing list exists, you must specify a real pickle file to import
from.
::

    >>> mlist = create_list('import@example.com')
    >>> command.process(FakeArgs)
    config.pck file is required

    >>> FakeArgs.pickle_file = [__file__]
    >>> command.process(FakeArgs)
    Not a Mailman 2.1 configuration file: .../import.rst

Now we can import the test pickle file.  As a simple illustration of the
import, the mailing list's 'real name' has changed.
::

    >>> from pkg_resources import resource_filename
    >>> FakeArgs.pickle_file = [
    ...     resource_filename('mailman.testing', 'config.pck')]

    >>> print mlist.display_name
    Import

    >>> command.process(FakeArgs)
    >>> print mlist.display_name
    Test
