================
REST API helpers
================

There are a number of helpers that make building out the REST API easier.


Resource paths
==============

For example, most resources don't have to worry about where they are rooted.
They only need to know where they are relative to the root URI, and this
function can return them the full path to the resource.

    >>> from mailman.rest.helpers import path_to
    >>> print path_to('system')
    http://localhost:9001/3.0/system

Parameters like the ``scheme``, ``host``, ``port``, and API version number can
be set in the configuration file.
::

    >>> config.push('helpers', """
    ... [webservice]
    ... hostname: geddy
    ... port: 2112
    ... use_https: yes
    ... api_version: 4.2
    ... """)

    >>> print path_to('system')
    https://geddy:2112/4.2/system


Etags
=====

HTTP *etags* are a way for clients to decide whether their copy of a resource
has changed or not.  Mailman's REST API calculates this in a cheap and dirty
way.  Pass in the dictionary representing the resource and that dictionary
gets modified to contain the etag under the ``http_etag`` key.

    >>> from mailman.rest.helpers import etag
    >>> resource = dict(geddy='bass', alex='guitar', neil='drums')
    >>> json_data = etag(resource)
    >>> print resource['http_etag']
    "43942176d8d5bb4414ccf35e2720ccd5251e66da"

For convenience, the etag function also returns the JSON representation of the
dictionary after tagging, since that's almost always what you want.
::

    >>> import json
    >>> data = json.loads(json_data)

    # This is pretty close to what we want, so it's convenient to use.
    >>> dump_msgdata(data)
    alex     : guitar
    geddy    : bass
    http_etag: "43942176d8d5bb4414ccf35e2720ccd5251e66da"
    neil     : drums


POST unpacking
==============

Another helper unpacks ``POST`` request variables, validating and converting
their values.
::

    >>> from mailman.rest.validator import Validator
    >>> validator = Validator(one=int, two=unicode, three=bool)

    >>> class FakeRequest:
    ...     POST = {}
    >>> FakeRequest.POST = dict(one='1', two='two', three='yes')

On valid input, the validator can be used as a ``**keyword`` argument.

    >>> def print_request(one, two, three):
    ...     print repr(one), repr(two), repr(three)
    >>> print_request(**validator(FakeRequest))
    1 u'two' True

On invalid input, an exception is raised.

    >>> FakeRequest.POST['one'] = 'hello'
    >>> print_request(**validator(FakeRequest))
    Traceback (most recent call last):
    ...
    ValueError: Cannot convert parameters: one

On missing input, an exception is raised.

    >>> del FakeRequest.POST['one']
    >>> print_request(**validator(FakeRequest))
    Traceback (most recent call last):
    ...
    ValueError: Missing parameters: one

If more than one key is missing, it will be reflected in the error message.

    >>> del FakeRequest.POST['two']
    >>> print_request(**validator(FakeRequest))
    Traceback (most recent call last):
    ...
    ValueError: Missing parameters: one, two

Extra keys are also not allowed.

    >>> FakeRequest.POST = dict(one='1', two='two', three='yes',
    ...                         four='', five='')
    >>> print_request(**validator(FakeRequest))
    Traceback (most recent call last):
    ...
    ValueError: Unexpected parameters: five, four

However, if optional keys are missing, it's okay.
::

    >>> validator = Validator(one=int, two=unicode, three=bool,
    ...                       four=int, five=int,
    ...                       _optional=('four', 'five'))

    >>> FakeRequest.POST = dict(one='1', two='two', three='yes',
    ...                         four='4', five='5')
    >>> def print_request(one, two, three, four=None, five=None):
    ...     print repr(one), repr(two), repr(three), repr(four), repr(five)
    >>> print_request(**validator(FakeRequest))
    1 u'two' True 4 5

    >>> del FakeRequest.POST['four']
    >>> print_request(**validator(FakeRequest))
    1 u'two' True None 5

    >>> del FakeRequest.POST['five']
    >>> print_request(**validator(FakeRequest))
    1 u'two' True None None

But if the optional values are present, they must of course also be valid.

    >>> FakeRequest.POST = dict(one='1', two='two', three='yes',
    ...                         four='no', five='maybe')
    >>> print_request(**validator(FakeRequest))
    Traceback (most recent call last):
    ...
    ValueError: Cannot convert parameters: five, four


Arrays
------

Some ``POST`` forms include more than one value for a particular key.  This is
how lists and arrays are modeled.  The validator does the right thing with
such form data.  Specifically, when a key shows up multiple times in the form
data, a list is given to the validator.
::

    # Of course we can't use a normal dictionary, but webob has a useful data
    # type we can use.
    >>> from webob.multidict import MultiDict
    >>> form_data = MultiDict(one='1', many='3')
    >>> form_data.add('many', '4')
    >>> form_data.add('many', '5')

This is a validation function that ensures the value is a list.

    >>> def must_be_list(value):
    ...     if not isinstance(value, list):
    ...         raise ValueError('not a list')
    ...     return [int(item) for item in value]

This is a validation function that ensure the value is *not* a list.

    >>> def must_be_scalar(value):
    ...     if isinstance(value, list):
    ...         raise ValueError('is a list')
    ...     return int(value)

And a validator to pull it all together.

    >>> validator = Validator(one=must_be_scalar, many=must_be_list)
    >>> FakeRequest.POST = form_data
    >>> values = validator(FakeRequest)
    >>> print values['one']
    1
    >>> print values['many']
    [3, 4, 5]

The list values are guaranteed to be in the same order they show up in the
form data.

    >>> from webob.multidict import MultiDict
    >>> form_data = MultiDict(one='1', many='3')
    >>> form_data.add('many', '5')
    >>> form_data.add('many', '4')
    >>> FakeRequest.POST = form_data
    >>> values = validator(FakeRequest)
    >>> print values['one']
    1
    >>> print values['many']
    [3, 5, 4]
