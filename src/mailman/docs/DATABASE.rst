========================
Setting up your database
========================

Mailman uses the Storm_ ORM to provide persistence of data in a relational
database.  By default, Mailman uses Python's built-in SQLite3_ database,
however, Storm is compatible with PostgreSQL_ and MySQL, among possibly
others.

Currently, Mailman is known to work with either the default SQLite3 database,
or PostgreSQL.  (Volunteers to port it to MySQL are welcome!).  If you want to
use SQLite3, you generally don't need to change anything, but if you want
Mailman to use PostgreSQL, you'll need to set that up first, and then change a
configuration variable in your `/etc/mailman.cfg` file.

Two configuration variables control which database Mailman uses.  The first
names the class implementing the database interface.  The second names the
Storm URL for connecting to the database.  Both variables live in the
`[database]` section of the configuration file.


SQLite3
=======

As mentioned, if you want to use SQLite3 in the default configuration, you
generally don't need to change anything.  However, if you want to change where
the SQLite3 database is stored, you can change the `url` variable in the
`[database]` section.  By default, the database is stored in the *data
directory* in the `mailman.db` file.  Here's how you'd force Mailman to store
its database in `/var/lib/mailman/sqlite.db` file::

    [database]
    url: sqlite:////var/lib/mailman/sqlite.db


PostgreSQL
==========

First, you need to configure PostgreSQL itself.  This `Ubuntu article`_ may
help.  Let's say you create the `mailman` database in PostgreSQL via::

    $ sudo -u postgres createdb -O myuser mailman

You would then need to set both the `class` and `url` variables in
`mailman.cfg` like so::

    [database]
    class: mailman.database.postgresql.PostgreSQLDatabase
    url: postgres://myuser:mypassword@mypghost/mailman

That should be it.

Note that if you want to run the full test suite against PostgreSQL, you
should make these changes to the `mailman/testing/test.cfg` file (yes,
eventually we'll make this easier), start up PostgreSQL and run `bin/test` as
normal.

If you have any problems, you may need to delete the database and re-create
it::

    $ sudo -u postgres dropdb mailman
    $ sudo -u postgres createdb -O myuser mailman

My thanks to Stephen A. Goss for his contribution of PostgreSQL support.


.. _Storm: http://storm.canonical.com
.. _SQLite3: http://docs.python.org/library/sqlite3.html
.. _PostgreSQL: http://www.postgresql.org/
.. _MySQL: http://dev.mysql.com/
.. _`Ubuntu article`: https://help.ubuntu.com/community/PostgreSQL
