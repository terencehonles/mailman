"""This is the module which take your site-specific settings.

See ./mm_defaults for the all the options.  Override only those you want to 
change, after the 'from mm_defaults import *' line.

Note that these are just default settings - many of them can be overridden
via the admin and user interfaces on a per-list and per-user basis.

Note also that some of the settings are resolved against the active list
setting by using the value as a format string against the
list-instance-object's dictionary - see the distributed value of
DEFAULT_MSG_FOOTER for an example."""

from mm_defaults import *

# Put your site specific configurations below here.

import os

MAILMAN_URL       = 'http://www.python.org/ftp/python/contrib/Network/mailman/'
MAX_SPAWNS        = 40
DEFAULT_HOST_NAME = 'python.org'
SENDMAIL_CMD      = '/usr/lib/sendmail -f %s %s'
DEFAULT_URL       = 'http://www.python.org/mailman'
ARCHIVE_URL       = 'http://www.python.org/~mailman/archives'
# Once we know our home directory we can figure out the rest.
HOME_DIR	  = '/home/mailman'
MAILMAN_DIR       = '/home/mailman/mailman'

# Subscription list restricted to list members until we finish spider hider.
DEFAULT_CLOSED = 1
