================================
Set up Postorius in five minutes
================================

This is a quick guide for setting up a development environment to work on
Mailman 3's web UI, called Postorius.  If all goes as planned, you should be
done within 5 minutes.  This has been tested on Ubuntu 11.04.

In order to download the components necessary you need to have the `Bazaar`_
version control system installed on your system.  Mailman and mailman.client
need at least Python version 2.6.

It's probably a good idea to set up a virtual Python environment using
`virtualenv`_.  `Here is a brief HOWTO`_.

.. _`virtualenv`: http://pypi.python.org/pypi/virtualenv
.. _`Here is a brief HOWTO`: ./ArchiveUIin5.html#get-it-running-under-virtualenv
.. _`Bazaar`: http://bazaar.canonical.com/en/


GNU Mailman 3
=============

First download the latest revision of Mailman 3 from Launchpad.
::

  $ bzr branch lp:mailman

Install and test::

  $ cd mailman
  $ python bootstrap.py
  $ bin/buildout
  $ bin/test

If you get no errors you can now start Mailman::

  $ bin/mailman start
  $ cd ..

At this point Mailman will not send nor receive any real emails.  But that's
fine as long as you only want to work on the components related to the REST
client or the web ui.


mailman.client (the Python bindings for Mailman's REST API)
===========================================================

Download from Launchpad::

  $ bzr branch lp:mailman.client

Install in development mode to be able to change the code without working
directly on the PYTHONPATH.
::

  $ cd mailman.client
  $ sudo python setup.py develop
  $ cd ..


Django >= 1.3
=============

Postorius is a pluggable Django application.  Therefore you need to have
Django (at least version 1.3) installed.
::

  $ wget http://www.djangoproject.com/download/1.3.1/tarball/ -O Django-1.3.1.tar.gz
  $ tar xzf Django-1.3.1.tar.gz
  $ cd Django-1.3.1
  $ sudo python setup.py install
  $ cd ..


Postorius
=========

::

  $ bzr branch lp:postorius
  $ cd postorius
  $ sudo python setup.py develop


Start the development server
============================

::

  $ cd dev_setup
  $ python manage.py syncdb
  $ python manage.py runserver

The last command will start the dev server on http://localhost:8000.


A note for MacOS X users (and possibly others running python 2.7)
=================================================================

*Note: These paragraphs are struck-through on the Mailman wiki.*

On an OS X 10.7 (Lion) system, some of these steps needed to be modified to
use python2.6 instead of python. (In particular, bzr is known to behave badly
when used python2.7 on OS X 10.7 at the moment -- hopefully this will be fixed
and no longer an issue soon.)

You will need to install the latest version of XCode on MacOS 10.7, which is
available for free from the App Store.  If you had a previous version of XCode
installed when you upgraded to 10.7, it will no longer work and will not have
automatically been upgraded, so be prepared to install again.  Once you have
it installed from the App Store, you will still need to go run the installer
from ``/Applications`` to complete the installation.
