# Copyright (C) 2006-2009 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import sys

from cStringIO import StringIO
from email import message_from_string
from urlparse import urlparse

from Mailman.configuration import config

# XXX Should this be configurable in Defaults.py?
STEALTH_MODE = False
MOVED_RESPONSE = '302 Found'
# Above is for debugging convenience.  We should use:
# MOVED_RESPONSE = '301 Moved Permanently'



def websafe(s):
    return s


SCRIPTS = ['admin', 'admindb', 'confirm', 'create',
           'edithtml', 'listinfo', 'options', 'private',
           'rmlist', 'roster', 'subscribe']
ARCHVIEW = ['private']

SLASH   = '/'
NL2     = '\n\n'
CRLF2   = '\r\n\r\n'

dotonly = re.compile(r'^\.+$')



# WSGI to CGI wrapper.  Mostly copied from scripts/driver.
def mailman_app(environ, start_response):
    """Wrapper to *.py CGI commands"""
    global STEALTH_MODE, websafe
    try:
        try:
            if not STEALTH_MODE:
                from Mailman.Utils import websafe
        except:
            STEALTH_MODE = True
            raise

        import logging
        log = logging.getLogger('mailman.error')

        from Mailman import i18n
        i18n.set_language(config.DEFAULT_SERVER_LANGUAGE)

        path = environ['PATH_INFO']
        paths = path.split(SLASH)
        # sanity check for paths
        spaths = [ i for i in paths[1:] if i and not dotonly.match(i) ]
        if spaths and spaths != paths[1:]:
            newpath = SLASH + SLASH.join(spaths)
            start_response(MOVED_RESPONSE, [('Location', newpath)])
            return 'Location: ' + newpath
        # find script name
        for script in SCRIPTS:
            if script in spaths:
                # Get script position in spaths and break.
                scrpos = spaths.index(script)
                break
        else:
            # Can't find valid script.
            start_response('404 Not Found', [])
            return '404 Not Found'
        # Compose CGI SCRIPT_NAME and PATH_INFO from WSGI path.
        script_name = SLASH + SLASH.join(spaths[:scrpos+1])
        environ['SCRIPT_NAME'] = script_name
        if len(paths) > scrpos+2:
            path_info = SLASH + SLASH.join(paths[scrpos+2:])
            if script in ARCHVIEW \
               and path_info.count('/') in (1,2) \
               and not paths[-1].split('.')[-1] in ('html', 'txt', 'gz'):
                # Add index.html if /private/listname or
                # /private/listname/YYYYmm is requested.
                newpath = script_name + path_info + '/index.html'
                start_response(MOVED_RESPONSE, [('Location', newpath)])
                return 'Location: ' + newpath
            environ['PATH_INFO'] = path_info
        else:
            environ['PATH_INFO'] = ''
        # Reverse proxy environment.
        if environ.has_key('HTTP_X_FORWARDED_HOST'):
            environ['HTTP_HOST'] = environ['HTTP_X_FORWARDED_HOST']
        if environ.has_key('HTTP_X_FORWARDED_FOR'):
            environ['REMOTE_HOST'] = environ['HTTP_X_FORWARDED_FOR']
        modname = 'Mailman.Cgi.' + script
        # Clear previous cookie before setting new one.
        os.environ['HTTP_COOKIE'] = ''
        for k, v in environ.items():
            os.environ[k] = str(v)
        # Prepare for redirection
        save_stdin = sys.stdin
        # CGI writes its output to sys.stdout, while wsgi app should
        # return (list of) strings.
        save_stdout = sys.stdout
        save_stderr = sys.stderr
        tmpstdout = StringIO()
        tmpstderr = StringIO()
        response = ''
        try:
            try:
                sys.stdin  = environ['wsgi.input']
                sys.stdout = tmpstdout
                sys.stderr = tmpstderr
                __import__(modname)
                sys.modules[modname].main()
                response = sys.stdout.getvalue()
            finally:
                sys.stdin  = save_stdin
                sys.stdout = save_stdout
                sys.stderr = save_stderr
        except SystemExit:
            sys.stdout.write(tmpstdout.getvalue())
        if response:
            try:
                head, content = response.split(NL2, 1)
            except ValueError:
                head, content = response.split(CRLF2, 1)
            m = message_from_string(head + CRLF2)
            start_response('200 OK', m.items())
            return [content]
        else:
            # TBD: Error Code/Message
            start_response('500 Server Error', [])
            return '500 Internal Server Error'
    except:
        start_response('200 OK', [('Content-Type', 'text/html')])
        retstring = print_traceback(log)
        retstring += print_environment(log)
        return retstring



# These functions are extracted and modified from scripts/driver.
#
# If possible, we print the error to two places.  One will always be stdout
# and the other will be the log file if a log file was created.  It is assumed
# that stdout is an HTML sink.
def print_traceback(log=None):
    try:
        import traceback
    except ImportError:
        traceback = None
    try:
        from mailman.version import VERSION
    except ImportError:
        VERSION = '&lt;undetermined&gt;'

    # Write to the log file first.
    if log:
        outfp = StringIO()

        print >> outfp, '@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@'
        print >> outfp, '[----- Mailman Version: %s -----]' % VERSION
        print >> outfp, '[----- Traceback ------]'
        if traceback:
            traceback.print_exc(file=outfp)
        else:
            print >> outfp, '[failed to import module traceback]'
            print >> outfp, '[exc: %s, var: %s]' % sys.exc_info()[0:2]
        # Don't use .exception() since that'll give us the exception twice.
        # IWBNI we could print directly to the log's stream, or treat a log
        # like an output stream.
        log.error('%s', outfp.getvalue())

    # return HTML sink.
    htfp = StringIO()
    print >> htfp, """\
<head><title>Bug in Mailman version %(VERSION)s</title></head>
<body bgcolor=#ffffff><h2>Bug in Mailman version %(VERSION)s</h2>
<p><h3>We're sorry, we hit a bug!</h3>
""" % locals()
    if not STEALTH_MODE:
        print >> htfp, '''<p>If you would like to help us identify the problem,
please email a copy of this page to the webmaster for this site with
a description of what happened.  Thanks!

<h4>Traceback:</h4><p><pre>'''
        exc_info = sys.exc_info()
        if traceback:
            for line in traceback.format_exception(*exc_info):
                print >> htfp, websafe(line)
        else:
            print >> htfp, '[failed to import module traceback]'
            print >> htfp, '[exc: %s, var: %s]' %\
                            [websafe(x) for x in exc_info[0:2]]
        print >> htfp, '\n\n</pre></body>'
    else:
        print >> htfp, '''<p>Please inform the webmaster for this site of this
problem.  Printing of traceback and other system information has been
explicitly inhibited, but the webmaster can find this information in the
Mailman error logs.'''
    return htfp.getvalue()



def print_environment(log=None):
    try:
        import os
    except ImportError:
        os = None

    if log:
        outfp = StringIO()

        # Write some information about our Python executable to the log file.
        print >> outfp, '[----- Python Information -----]'
        print >> outfp, 'sys.version     =', sys.version
        print >> outfp, 'sys.executable  =', sys.executable
        print >> outfp, 'sys.prefix      =', sys.prefix
        print >> outfp, 'sys.exec_prefix =', sys.exec_prefix
        print >> outfp, 'sys.path        =', sys.exec_prefix
        print >> outfp, 'sys.platform    =', sys.platform

    # Write the same information to the HTML sink.
    htfp = StringIO()
    if not STEALTH_MODE:
        print >> htfp, """\
<p><hr><h4>Python information:</h4>

<p><table>
<tr><th>Variable</th><th>Value</th></tr>
<tr><td><tt>sys.version</tt></td><td> %s </td></tr>
<tr><td><tt>sys.executable</tt></td><td> %s </td></tr>
<tr><td><tt>sys.prefix</tt></td><td> %s </td></tr>
<tr><td><tt>sys.exec_prefix</tt></td><td> %s </td></tr>
<tr><td><tt>sys.path</tt></td><td> %s </td></tr>
<tr><td><tt>sys.platform</tt></td><td> %s </td></tr>
</table>""" % (sys.version, sys.executable, sys.prefix,
               sys.exec_prefix, sys.path, sys.platform)

    # Write environment variables to the log file.
    if log:
        print >> outfp, '[----- Environment Variables -----]'
        if os:
            for k, v in os.environ.items():
                print >> outfp, '\t%s: %s' % (k, v)
        else:
            print >> outfp, '[failed to import module os]'

    # Write environment variables to the HTML sink.
    if not STEALTH_MODE:
        print >> htfp, """\
<p><hr><h4>Environment variables:</h4>

<p><table>
<tr><th>Variable</th><th>Value</th></tr>
"""
        if os:
            for k, v in os.environ.items():
                print >> htfp, '<tr><td><tt>' + websafe(k) + \
                      '</tt></td><td>' + websafe(v) + \
                      '</td></tr>'
            print >> htfp, '</table>'
        else:
            print >> htfp, '<p><hr>[failed to import module os]'

    # Dump the log output
    if log:
        log.error('%s', outfp.getvalue())

    return htfp.getvalue()
