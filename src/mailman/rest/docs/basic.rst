===========
REST server
===========

Mailman exposes a REST HTTP server for administrative control.

The server listens for connections on a configurable host name and port.

It is always protected by HTTP basic authentication using a single global
username and password. The credentials are set in the webservice section
of the config using the admin_user and admin_pass properties.

Because the REST server has full administrative access, it should always be
run only on localhost, unless you really know what you're doing.  In addition
you should set the username and password to secure values and distribute them
to any REST clients with reasonable precautions.

The Mailman major and minor version numbers are in the URL.

System information can be retrieved from the server.  By default JSON is
returned.

    >>> dump_json('http://localhost:9001/3.0/system')
    http_etag: "..."
    mailman_version: GNU Mailman 3.0... (...)
    python_version: ...
    self_link: http://localhost:9001/3.0/system


Non-existent links
==================

When you try to access a link that doesn't exist, you get the appropriate HTTP
404 Not Found error.

    >>> dump_json('http://localhost:9001/3.0/does-not-exist')
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found


Invalid credentials
===================

When you try to access the REST server using invalid credentials you will get
an appropriate HTTP 401 Unauthorized error.
::

    >>> from base64 import b64encode
    >>> auth = b64encode('baduser:badpass')

    >>> url = 'http://localhost:9001/3.0/system'
    >>> headers = {
    ...     'Content-Type': 'application/x-www-form-urlencode',
    ...     'Authorization': 'Basic ' + auth,
    ...     }

    >>> from httplib2 import Http
    >>> response, content = Http().request(url, 'GET', None, headers)
    >>> print content
    401 Unauthorized
    <BLANKLINE>
    User is not authorized for the REST API
    <BLANKLINE>

But with the right headers, the request succeeds.

    >>> auth = b64encode('{0}:{1}'.format(config.webservice.admin_user,
    ...                                   config.webservice.admin_pass))
    >>> headers['Authorization'] = 'Basic ' + auth
    >>> response, content = Http().request(url, 'GET', None, headers)
    >>> print response.status
    200


.. _REST: http://en.wikipedia.org/wiki/REST
