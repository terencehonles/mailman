============
The scrubber
============

The scrubber is an integral part of Mailman, both in the normal delivery of
messages and in components such as the archiver.  Its primary purpose is to
scrub attachments from messages so that binary goop doesn't end up in an
archive message.

    >>> mlist = create_list('_xtest@example.com')
    >>> mlist.preferred_language = 'en'

Helper functions for getting the attachment data.
::

    >>> import os, re
    >>> def read_attachment(filename, remove=True):
    ...     path = os.path.join(config.PRIVATE_ARCHIVE_FILE_DIR,
    ...                         mlist.fqdn_listname, filename)
    ...     fp = open(path)
    ...     try:
    ...         data = fp.read()
    ...     finally:
    ...         fp.close()
    ...     if remove:
    ...         os.unlink(path)
    ...     return data

    >>> from urlparse import urlparse
    >>> def read_url_from_message(msg):
    ...     url = None
    ...     for line in msg.get_payload().splitlines():
    ...         mo = re.match('URL: <(?P<url>[^>]+)>', line)
    ...         if mo:
    ...             url = mo.group('url')
    ...             break
    ...     path = '/'.join(urlparse(url).path.split('/')[3:])
    ...     return read_attachment(path)


Saving attachments
==================

The Scrubber handler exposes a function called ``save_attachment()`` which can
be used to strip various types of attachments and store them in the archive
directory.  This is a public interface used by components outside the normal
processing pipeline.

Site administrators can decide whether the scrubber should use the attachment
filename suggested in the message's ``Content-Disposition:`` header or not.
If enabled, the filename will be used when this header attribute is present
(yes, this is an unfortunate double negative).
::

    >>> config.push('test config', """
    ... [scrubber]
    ... use_attachment_filename: yes
    ... """)
    >>> msg = message_from_string("""\
    ... Content-Type: image/gif; name="xtest.gif"
    ... Content-Transfer-Encoding: base64
    ... Content-Disposition: attachment; filename="xtest.gif"
    ... 
    ... R0lGODdhAQABAIAAAAAAAAAAACwAAAAAAQABAAACAQUAOw==
    ... """)

    >>> from mailman.pipeline.scrubber import save_attachment
    >>> print save_attachment(mlist, msg, 'dir')
    <http://www.example.com/pipermail/_xtest@example.com/dir/xtest.gif>
    >>> data = read_attachment('dir/xtest.gif')
    >>> print data[:6]
    GIF87a
    >>> len(data)
    34

Saving the attachment does not alter the original message.

    >>> print msg.as_string()
    Content-Type: image/gif; name="xtest.gif"
    Content-Transfer-Encoding: base64
    Content-Disposition: attachment; filename="xtest.gif"
    <BLANKLINE>
    R0lGODdhAQABAIAAAAAAAAAAACwAAAAAAQABAAACAQUAOw==

The site administrator can also configure Mailman to ignore the
``Content-Disposition:`` filename.  This is the default.

    >>> config.pop('test config')
    >>> config.push('test config', """
    ... [scrubber]
    ... use_attachment_filename: no
    ... """)
    >>> msg = message_from_string("""\
    ... Content-Type: image/gif; name="xtest.gif"
    ... Content-Transfer-Encoding: base64
    ... Content-Disposition: attachment; filename="xtest.gif"
    ... 
    ... R0lGODdhAQABAIAAAAAAAAAAACwAAAAAAQABAAACAQUAOw==
    ... """)
    >>> print save_attachment(mlist, msg, 'dir')
    <http://www.example.com/pipermail/_xtest@example.com/dir/attachment.gif>
    >>> data = read_attachment('dir/xtest.gif')
    Traceback (most recent call last):
    IOError: [Errno ...] No such file or directory:
        u'.../archives/private/_xtest@example.com/dir/xtest.gif'
    >>> data = read_attachment('dir/attachment.gif')
    >>> print data[:6]
    GIF87a
    >>> len(data)
    34


Scrubbing image attachments
===========================

When scrubbing image attachments, the original message is modified to include
a reference to the attachment file as available through the on-line archive.

    >>> msg = message_from_string("""\
    ... MIME-Version: 1.0
    ... Content-Type: multipart/mixed; boundary="BOUNDARY"
    ...
    ... --BOUNDARY
    ... Content-type: text/plain; charset=us-ascii
    ... 
    ... This is a message.
    ... --BOUNDARY
    ... Content-Type: image/gif; name="xtest.gif"
    ... Content-Transfer-Encoding: base64
    ... Content-Disposition: attachment; filename="xtest.gif"
    ... 
    ... R0lGODdhAQABAIAAAAAAAAAAACwAAAAAAQABAAACAQUAOw==
    ... --BOUNDARY--
    ... """)
    >>> msgdata = {}

The ``Scrubber.process()`` function is different than other handler process
functions in that it returns the scrubbed message.

    >>> from mailman.pipeline.scrubber import process
    >>> scrubbed_msg = process(mlist, msg, msgdata)
    >>> scrubbed_msg is msg
    True
    >>> print scrubbed_msg.as_string()
    MIME-Version: 1.0
    Message-ID: ...
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    <BLANKLINE>
    This is a message.
    -------------- next part --------------
    A non-text attachment was scrubbed...
    Name: xtest.gif
    Type: image/gif
    Size: 34 bytes
    Desc: not available
    URL: <http://www.example.com/pipermail/_xtest@example.com/attachments/.../attachment.gif>
    <BLANKLINE>

This is the same as the transformed message originally passed in.

    >>> print msg.as_string()
    MIME-Version: 1.0
    Message-ID: ...
    Content-Type: text/plain; charset="us-ascii"
    Content-Transfer-Encoding: 7bit
    <BLANKLINE>
    This is a message.
    -------------- next part --------------
    A non-text attachment was scrubbed...
    Name: xtest.gif
    Type: image/gif
    Size: 34 bytes
    Desc: not available
    URL: <http://www.example.com/pipermail/_xtest@example.com/attachments/.../attachment.gif>
    <BLANKLINE>
    >>> msgdata
    {}

The URL will point to the attachment sitting in the archive.

    >>> data = read_url_from_message(msg)
    >>> data[:6]
    'GIF87a'
    >>> len(data)
    34


Scrubbing text attachments
==========================

Similar to image attachments, text attachments will also be scrubbed, but the
placeholder will be slightly different.

    >>> msg = message_from_string("""\
    ... MIME-Version: 1.0
    ... Content-Type: multipart/mixed; boundary="BOUNDARY"
    ...
    ... --BOUNDARY
    ... Content-type: text/plain; charset=us-ascii; format=flowed; delsp=no
    ...
    ... This is a message.
    ... --BOUNDARY
    ... Content-type: text/plain; name="xtext.txt"
    ... Content-Disposition: attachment; filename="xtext.txt"
    ...
    ... This is a text attachment.
    ... --BOUNDARY--
    ... """)
    >>> scrubbed_msg = process(mlist, msg, {})
    >>> print scrubbed_msg.as_string()
    MIME-Version: 1.0
    Message-ID: ...
    Content-Transfer-Encoding: 7bit
    Content-Type: text/plain; charset="us-ascii"; format="flowed"; delsp="no"
    <BLANKLINE>
    This is a message.
    -------------- next part --------------
    An embedded and charset-unspecified text was scrubbed...
    Name: xtext.txt
    URL: <http://www.example.com/pipermail/_xtest@example.com/attachments/.../attachment.txt>
    <BLANKLINE>
    >>> read_url_from_message(msg)
    'This is a text attachment.'


Clean up
========

    >>> config.pop('test config')
