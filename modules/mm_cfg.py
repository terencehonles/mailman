# This file needs to get auto-generated.
# As much of it as possible should be gleaned w/o prompting the user.

import os

MAILMAN_URL       = 'http://www.python.org/'
MAX_SPAWNS        = 40
DEFAULT_HOST_NAME = 'python.org'

VERSION           = '1.0b1'
# Our home directory.  Once we know this, we can figure out other things
# for ourselves
HOME_DIR	  = '/home/mailman'
MAILMAN_DIR       = '/home/mailman/mailman'
# I don't think this is used any more
MAIL_LOG          = '/var/log/maillog'
LIST_DATA_DIR     = os.path.join(MAILMAN_DIR, 'lists')
HTML_DIR	  = os.path.join(HOME_DIR, 'public_html')
CGI_DIR           = os.path.join(HOME_DIR, 'cgi-bin')
LOCK_DIR          = os.path.join(MAILMAN_DIR, 'locks')
SENDMAIL_CMD      = '/usr/lib/sendmail -f %s %s'
DEFAULT_URL       = 'http://%s/mailman/' % DEFAULT_HOST_NAME
TEMPLATE_DIR      = os.path.join(MAILMAN_DIR, 'templates')
ARCHIVE_URL       = 'http://%s/~mailman/archives' % DEFAULT_HOST_NAME
HOME_PAGE         = 'index.html'
MAILMAN_OWNER     = 'mailman@%s' % DEFAULT_HOST_NAME


# Enumeration for types of configurable variables in Mailman.
Toggle    = 1
Radio     = 2
String    = 3
Text      = 4
Email     = 5
EmailList = 6
Host      = 7
Number    = 8

# could add Directory and URL


# Bitfield for user options
Digests             = 0 # handled by other mechanism, doesn't need a flag.
DisableDelivery     = 1
DontReceiveOwnPosts = 2 # Non-digesters only
AcknowlegePosts     = 4
EnableMime          = 8 # Digesters only
ConcealSubscription = 16
