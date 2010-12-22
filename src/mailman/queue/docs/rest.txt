===========
REST server
===========

Mailman is controllable through an administrative `REST`_ HTTP server.

    >>> from mailman.testing import helpers
    >>> master = helpers.TestableMaster(helpers.wait_for_webservice)
    >>> master.start('rest')

The RESTful server can be used to access basic version information.

    >>> dump_json('http://localhost:9001/3.0/system')
    http_etag: "..."
    mailman_version: GNU Mailman 3.0... (...)
    python_version: ...
    self_link: http://localhost:9001/3.0/system


Clean up
========

    >>> master.stop()

.. _REST: http://en.wikipedia.org/wiki/REST
