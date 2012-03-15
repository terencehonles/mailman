==========================
Operating on mailing lists
==========================

The ``withlist`` command is a pretty powerful way to operate on mailing lists
from the command line.  This command allows you to interact with a list at a
Python prompt, or process one or more mailing lists through custom made Python
functions.

XXX Test the interactive operation of withlist


Getting detailed help
=====================

Because ``withlist`` is so complex, you need to request detailed help.
::

    >>> from mailman.commands.cli_withlist import Withlist
    >>> command = Withlist()

    >>> class FakeArgs:
    ...     interactive = False
    ...     run = None
    ...     details = True
    ...     listname = []

    >>> class FakeParser:
    ...     def error(self, message):
    ...         print message
    >>> command.parser = FakeParser()

    >>> args = FakeArgs()
    >>> command.process(args)
    This script provides you with a general framework for interacting with a
    mailing list.
    ...


Running a command
=================

By putting a Python function somewhere on your ``sys.path``, you can have
``withlist`` call that function on a given mailing list.  The function takes a
single argument, the mailing list.
::

    >>> import os, sys
    >>> old_path = sys.path[:]
    >>> sys.path.insert(0, config.VAR_DIR)

    >>> with open(os.path.join(config.VAR_DIR, 'showme.py'), 'w') as fp:
    ...     print >> fp, """\
    ... def showme(mailing_list):
    ...     print "The list's name is", mailing_list.fqdn_listname
    ...
    ... def displayname(mailing_list):
    ...     print "The list's display name is", mailing_list.display_name
    ... """

If the name of the function is the same as the module, then you only need to
name the function once.

    >>> mlist = create_list('aardvark@example.com')
    >>> args.details = False
    >>> args.run = 'showme'
    >>> args.listname = 'aardvark@example.com'
    >>> command.process(args)
    The list's name is aardvark@example.com

The function's name can also be different than the modules name.  In that
case, just give the full module path name to the function you want to call.

    >>> args.run = 'showme.displayname'
    >>> command.process(args)
    The list's display name is Aardvark


Multiple lists
==============

You can run a command over more than one list by using a regular expression in
the `listname` argument.  To indicate a regular expression is used, the string
must start with a caret.
::

    >>> mlist_2 = create_list('badger@example.com')
    >>> mlist_3 = create_list('badboys@example.com')

    >>> args.listname = '^.*example.com'
    >>> command.process(args)
    The list's display name is Aardvark
    The list's display name is Badger
    The list's display name is Badboys

    >>> args.listname = '^bad.*'
    >>> command.process(args)
    The list's display name is Badger
    The list's display name is Badboys

    >>> args.listname = '^foo'
    >>> command.process(args)


Error handling
==============

You get an error if you try to run a function over a non-existent mailing
list.

    >>> args.listname = 'mystery@example.com'
    >>> command.process(args)
    No such list: mystery@example.com

You also get an error if no mailing list is named.

    >>> args.listname = None
    >>> command.process(args)
    --run requires a mailing list name


IPython
=======

You can use `IPython`_ as the interactive shell by changing certain
configuration variables in the `[shell]` section of your `mailman.cfg` file.
Set `use_ipython` to "yes" to switch to IPython, which must be installed on
your system.

Other configuration variables in the `[shell]` section can be used to
configure other aspects of the interactive shell.  You can change both the
prompt and the banner.


.. Clean up
   >>> sys.path = old_path

.. _`IPython`: http://ipython.org/
