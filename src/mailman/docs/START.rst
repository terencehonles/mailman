================================
Getting started with GNU Mailman
================================

Copyright (C) 2008-2011 by the Free Software Foundation, Inc.


Alpha Release
=============

The Mailman 3 alpha releases are being provided to give developers and other
interested people an early look at the next major version.  As such, some
things may not work yet.  Your participation is encouraged.  Your feedback and
contributions are welcome.  Please submit bug reports on the Mailman bug
tracker at https://bugs.launchpad.net/mailman though you will currently need
to have a login on Launchpad to do so.  You can also send email to the
mailman-developers@python.org mailing list.


Using the Alpha
===============

Python 2.6 or 2.7 is required.  It can either be the default 'python' on your
$PATH or it can be accessible via the ``python2.6`` or ``python2.7`` binary.
If your operating system does not include Python, see http://www.python.org
downloading and installing it from source.  Python 3 is not yet supported.


Building Mailman 3
==================

Mailman 3 is now based on the `zc.buildout`_ infrastructure, which greatly
simplifies building and testing Mailman.

You do not need anything other than Python and an internet connection to get
all the other Mailman 3 dependencies.  Here are the commands to build
everything::

    % python bootstrap.py
    % bin/buildout

Sit back and have some Kombucha while you wait for everything to download and
install.

Now you can run the test suite via::

    % bin/test -vv

You should see no failures.

Build the online docs by running::

    % bin/docs

(You might get warnings which you can safely ignore.)  Then visit

    parts/docs/mailman/build/mailman/docs/README.html

in your browser to start reading the documentation.  Or you can just read the
doctests by looking in all the 'doc' directories under the 'mailman' package.
Doctests are documentation first, so they should give you a pretty good idea
how various components of Mailman 3 works.


Running Mailman 3
=================

What, you actually want to *run* Mailman 3?  Oh well, if you insist.  You
will need to set up a configuration file to override the defaults and set
things up for your environment.  Mailman is configured via the `lazr.config`_
package which is really just a fancy ini-style configuration system.

``src/mailman/config/schema.cfg`` defines the ini-file schema and contains
documentation for every section and configuration variable.  Sections that end
in `.template` or `.master` are templates that must be overridden in actual
configuration files.  There is a default configuration file that defines these
basic overrides in ``src/mailman/config/mailman.cfg``.  Your own configuration
file will override those.

By default, all runtime files are put under a `var` directory in the current
working directory.

Mailman searches for its configuration file using the following search path.
The first existing file found wins.

 * ``-C config`` command line option
 * ``$MAILMAN_CONFIG_FILE`` environment variable
 * ``./mailman.cfg``
 * ``~/.mailman.cfg``
 * ``/etc/mailman.cfg``

Run the ``bin/mailman info`` command to see which configuration file Mailman
will use, and where it will put its database file.  The first time you run
this, Mailman will also create any necessary run-time directories and log
files.

Try ``bin/mailman --help`` for more details.  You can use the commands
``bin/mailman start`` to start the runner subprocess daemons, and of course
``bin/mailman stop`` to stop them.

The `web ui`_ is being developed as a separate, Django-based project.  For
now, all configuration happens via the command line and REST API.


.. _`zc.buildout`: http://pypi.python.org/pypi/zc.buildout
.. _`lazr.config`: http://pypi.python.org/pypi/lazr.config
.. _`web ui`: https://launchpad.net/mailmanweb
