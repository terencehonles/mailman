================================================
Mailman - The GNU Mailing List Management System
================================================

This is `GNU Mailman`_, a mailing list management system distributed under the
terms of the `GNU General Public License`_ (GPL) version 3 or later.

Mailman is written in Python_, a free object-oriented programming language.
Python is available for all platforms that Mailman is supported on, which
includes GNU/Linux and most other Unix-like operating systems (e.g. Solaris,
\*BSD, MacOSX, etc.).  Mailman is not supported on Windows, although web and
mail clients on any platform should be able to interact with Mailman just
fine.


Copyright
=========

Copyright 1998-2009 by the Free Software Foundation, Inc.

This file is part of GNU Mailman.

GNU Mailman is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

GNU Mailman is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.


Spelling
========

The name of this software is spelled `Mailman` with a leading capital `M`
but with a lower case second `m`.  Any other spelling is incorrect.  Its full
name is `GNU Mailman` but is often referred colloquially as `Mailman`.


History
=======

Mailman was originally developed by John Viega.  Subsequent development
(through version 1.0b3) was by Ken Manheimer.  Further work towards the 1.0
final release was a group effort, with the core contributors being: Barry
Warsaw, Ken Manheimer, Scott Cotton, Harald Meland, and John Viega.  Version
1.0 and beyond have been primarily maintained by Barry Warsaw with
contributions from many; see the ACKNOWLEDGMENTS file for details.  Jeremy
Hylton helped considerably with the Pipermail code in Mailman 2.0.  Mailman
2.1 is now being primarily maintained by Mark Sapiro and Tokio Kikuchi.  Barry
Warsaw is the lead developer on Mailman 3.


Help
====

The Mailman home page is:

    http://www.list.org

with mirrors at:

    http://www.gnu.org/software/mailman
    http://mailman.sf.net

The community driven wiki (including the FAQ_) is at:

    http://wiki.list.org

Other help resources, such as on-line documentation, links to the mailing
lists and archives, etc., are available at:

    http://www.list.org/help.html

For more information about the alpha releases, see `ALPHA.txt`_.


Requirements
============

Mailman 3.0 requires `Python 2.6`_ or newer.


.. _`GNU Mailman`: http://www.list.org
.. _`GNU General Public License`: http://www.gnu.org/licenses/gpl.txt
.. _Python: http://www.python.org
.. _FAQ: http://wiki.list.org/display/DOC/Frequently+Asked+Questions
.. _`Python 2.6`: http://www.python.org/download/releases/2.6.2/
.. _`ALPHA.txt`: ALPHA.html


Table of Contents
=================

.. toctree::
    :glob:

    *
    ../bin/docs/*
    ../commands/docs/*
    ../pipeline/docs/*
    ../queue/docs/*
    ../rest/docs/*
    ../rules/docs/*
    ../archiving/docs/*
    ../mta/docs/*
