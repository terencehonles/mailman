=====================================
Set up the archive ui in five minutes
=====================================

The `hyperkitty`_ application aims at providing an interface to visualize and
explore Mailman archives.

This is a `Django`_ project.

Requirements
============

- A mail archive in `maildir format`_ (no, you don't need a running Mailman
  3!)  Eventually hyperkitty will support `mbox format`_ for backward
  compatibility with *Pipermail*, and *zipped maildirs* seem like a good idea
  to save space.  **Beware:** Although you'd think that we would be able to
  manipulate the venerable *mbox* format safely and efficiently, that doesn't
  seem to be the case.  *Maildir* archives are **strongly** preferred, because
  they are more robust to program bugs (whether in Mailman, hyperkitty, or in
  the originating MUA!)
- Django is the web framework that supports the UI.
- `bunch`_ DOES WHAT?
- The `notmuch mail indexer`_ is used to generate indexes (and requires
  `Xapian`_).
- hyperkitty itself, which is a UI, and not responsible for maintaining the
  message archive itself.  (Since the archive is in `maildir format`_, any
  modern MTA or MDA can build one for you.)


Get it running (under virtualenv):
----------------------------------

It is generally a good idea to use `virtualenv`_ to create a stable
environment for your Python applications.

- Create the virtualenv::

    % virtualenv mailman3

- Activate the virtualenv::

    % cd mailman3
    % source bin/activate

You don't *have* to use virtualenv, though, and if you don't want to, just
omit the preceding steps.  Continue with these steps.

- Install Django and dependencies::

    % easy_install django
    % easy_install bunch

- Install notmuch -- these are bindings that come with the notmuch C library.
  The easiest way is probably to install them for your OS vendor and then
  symlink them into the virtualenv similar to this::

    % yum install -y python-notmuch

- Note: on a multiarch system like Fedora, the directories may be lib64 rather
  than lib on 64 bit systems.  Next::

    % cd lib/python2.7/site-packages
    % ln -s /usr/lib/python2.7/site-packages/notmuch .

- Note: this is the version of notmuch I tested with; others may work::

    % ln -s /usr/lib/python2.7/site-packages/notmuch-0.11-py2.7.egg-info .

- Install the hyperkitty sources::

    % git clone http://ambre.pingoured.fr/cgit/hyperkitty.git/


Running hyperkitty
------------------

- Start it::

    % cd hyperkitty

- Put the static content where it should be::

    % python manage.py collectstatic

- Run the Django server::

    % python manage.py runserver


.. _`hyperkitty`: https://launchpad.net/hyperkitty
.. _`Django`: http://djangoproject.org/
.. _`notmuch mail indexer`: http://notmuchmail.org
.. _`bunch`: http://pypi.python.org/pypi/bunch
.. _`Xapian`: http://xapian.org/
.. _`maildir format`: http://en.wikipedia.org/wiki/Maildir
.. _`mbox format`: http://en.wikipedia.org/wiki/Mbox
.. _`virtualenv`: http://pypi.python.org/pypi/virtualenv
