"""Distributed default settings for significant mailman config variables.

You should NOT edit the values here unless you're changing settings for
distribution.  For site-specific settings, put your definitions in
mm_cfg.py after the point at which it includes (via 'from ... import *')
this file, to override the distributed defaults with site-specific ones.
"""

import os

VERSION           = '1.0b1.1'
__version__ = VERSION + "$Revision: 149 $"

		   # Many site-specific settings #

MAILMAN_URL       = 'http://www.python.org/ftp/python/contrib/Network/mailman/'
DEFAULT_HOST_NAME = 'OVERRIDE.WITH.YOUR.MX.NAME'
SENDMAIL_CMD      = '/usr/lib/sendmail -f %s %s' # yours may be different
DEFAULT_URL       = 'http://www.OVERRIDE.WITH.YOUR.HOST/mailman/'
ARCHIVE_URL       = 'http://www.OVERRIDE.WITH.YOUR.ARCHIVE.DIR/'
# Once we know our home directory we can figure out the rest.
HOME_DIR	  = '/home/mailman'		# Override if you change
MAILMAN_DIR       = '/home/mailman/mailman'	# Override if you change
LIST_DATA_DIR     = os.path.join(MAILMAN_DIR, 'lists')
HTML_DIR	  = os.path.join(HOME_DIR, 'public_html')
CGI_DIR           = os.path.join(HOME_DIR, 'cgi-bin')
LOG_DIR           = os.path.join(HOME_DIR, 'logs')
LOCK_DIR          = os.path.join(MAILMAN_DIR, 'locks')
TEMPLATE_DIR      = os.path.join(MAILMAN_DIR, 'templates')
HOME_PAGE         = 'index.html'
MAILMAN_OWNER     = 'mailman-owner@%s' % DEFAULT_HOST_NAME

# System ceiling on number of batches into which deliveries are divided:
MAX_SPAWNS        = 40

			 # General Defaults #

DEFAULT_FILTER_PROG = ''
# Default number of batches in which to divide large deliveries:
DEFAULT_NUM_SPAWNS = 5
DEFAULT_LIST_ADVERTISED = 1
DEFAULT_MAX_NUM_RECIPIENTS = 10
DEFAULT_MAX_MESSAGE_SIZE = 40		# KB

# These format strings will be expanded w.r.t. the dictionary for the
# maillist instance.
DEFAULT_SUBJECT_PREFIX  = "[%(real_name)s] "
DEFAULT_MSG_HEADER = ""
DEFAULT_MSG_FOOTER = """----------------------------
%(real_name)s maillist
%(web_page_url)slistinfo/%(_internal_name)s
"""

		     # List Accessibility Defaults #

DEFAULT_MODERATED = 0
# Bounce if 'to' or 'cc' fields don't explicitly name list (anti-spam)?
DEFAULT_REQUIRE_EXPLICIT_DESTINATION = 1
# {header-name: regexp} spam filtering - we include one for example sake!
DEFAULT_BOUNCE_MATCHING_HEADERS = """
to: friend@public.com
"""
# Replies to posts inherently directed to list or original sender?
DEFAULT_REPLY_GOES_TO_LIST = 0
# Admin approval unnecessary for subscribes?
DEFAULT_AUTO_SUBSCRIBE = 1
# Is view of subscription list restricted to list members?
DEFAULT_CLOSED = 0
# Make it 1 when it works.
DEFAULT_MEMBER_POSTING_ONLY = 0
# 1 for email subscription verification, 2 for admin confirmation:
DEFAULT_WEB_SUBSCRIBE_REQUIRES_CONFIRMATION = 1

		     # Digestification Defaults #

# Can we get mailing list in non-digest format?
DEFAULT_NONDIGESTABLE = 1
# Can we get mailing list in digest format?
DEFAULT_DIGESTABLE = 1
DEFAULT_DIGEST_IS_DEFAULT = 0
DEFAULT_DIGEST_SIZE_THRESHOLD = 30	# KB
# 0 = never, 1 = daily, 2 = hourly:
DEFAULT_ARCHIVE_UPDATE_FREQUENCY = 2
# 0 = yearly, 1 = monthly
DEFAULT_ARCHIVE_VOLUME_FREQUENCY = 0
# Retain a flat text mailbox of postings as well as the fancy archives?
DEFAULT_ARCHIVE_RETAIN_TEXT_COPY = 1

		    # Bounce Processing Defaults #

# Should we do any bounced mail checking at all?
DEFAULT_BOUNCE_PROCESSING = 0 
# Minimum number of days that address has been undeliverable before 
# we consider nuking it..
DEFAULT_MINIMUM_REMOVAL_DATE = 5
# Minimum number of bounced posts to the list before we consider nuking it.
DEFAULT_MINIMUM_POST_COUNT_BEFORE_REMOVAL = 3
# 0 means no, 1 means yes but send admin a report,
# 2 means nuke 'em all and don't tell me (whee:)
DEFAULT_AUTOMATICALLY_REMOVE = 0
# Maximum number of posts that can go by w/o a bounce before we figure your
# problem must have gotten resolved...  usually this could be 1, but we
# need to account for lag time in getting the error messages.  I'd set this
# to the maximum number of messages you'd expect your list to reasonably
# get in 1 hour.
DEFAULT_MAX_POSTS_BETWEEN_BOUNCES = 5

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
