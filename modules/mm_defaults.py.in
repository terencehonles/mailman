"""Distributed default settings for significant mailman config variables.

You should NOT edit the values here unless you're changing settings for
distribution.  For site-specific settings, put your definitions in
mm_cfg.py after the point at which it includes (via 'from ... import *')
this file, to override the distributed defaults with site-specific ones.
"""

import os

VERSION           = '1.0b1.2'
__version__ = "$Revision: 445 $"

		   # Many site-specific settings #

MAILMAN_URL       = 'http://www.python.org/ftp/python/contrib/Network/mailman/'
DEFAULT_HOST_NAME = 'OVERRIDE.WITH.YOUR.MX.OR.HOST.NAME'
SMTPHOST	  = 'localhost'
SENDMAIL_CMD      = '/usr/lib/sendmail -f %s %s'     # yours may be different
DEFAULT_URL       = 'http://www.OVERRIDE.WITH.YOUR.HOST/mailman/'
PUBLIC_ARCHIVE_URL = 'http://www.OVERRIDE.WITH.YOUR.PUBLIC.ARCHIVE.URL/'
PRIVATE_ARCHIVE_URL = 'http://www.OVERRIDE.WITH.YOUR.PRIVATE.ARCHIVE.URL/'
# Once we know our home directory we can figure out the rest.
# BUT, if you override these in mm_cfg.py, you have to override the dependants
#      as well.
HOME_DIR	  = '/home/mailman'
MAILMAN_DIR       = '/home/mailman/mailman'
LIST_DATA_DIR     = os.path.join(MAILMAN_DIR, 'lists')
HTML_DIR	  = os.path.join(HOME_DIR, 'public_html')
CGI_DIR           = os.path.join(HOME_DIR, 'cgi-bin')
LOG_DIR           = os.path.join(HOME_DIR, 'logs')
LOCK_DIR          = os.path.join(MAILMAN_DIR, 'locks')
TEMPLATE_DIR      = os.path.join(MAILMAN_DIR, 'templates')
PUBLIC_ARCHIVE_FILE_DIR    = os.path.join(HOME_DIR, 'archives/public')
PRIVATE_ARCHIVE_FILE_DIR   = os.path.join(HOME_DIR, 'archives/private')
DEFAULT_ARCHIVE_PRIVATE    = 0		# 0=public, 1=private
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
DEFAULT_MSG_FOOTER = """------------------------------------------------------
%(real_name)s maillist  -  %(real_name)s@%(host_name)s
%(web_page_url)slistinfo/%(_internal_name)s
"""

		     # List Accessibility Defaults #

# Is admin notified of admin requests immediately by mail, as well as by
# daily pending-request reminder?
DEFAULT_ADMIN_IMMED_NOTIFY = 1
DEFAULT_MODERATED = 0
# Bounce if 'to' or 'cc' fields don't explicitly name list (anti-spam)?
DEFAULT_REQUIRE_EXPLICIT_DESTINATION = 1
# Alternate names acceptable as explicit destinations for this list.
DEFAULT_ACCEPTABLE_ALIASES ="""
"""
# {header-name: regexp} spam filtering - we include some for example sake.
DEFAULT_BOUNCE_MATCHING_HEADERS = """
# Lines that *start* with a '#' are comments.
to: friend@public.com
message-id: relay.comanche.denmark.eu
from: list@listme.com
from: .*@uplinkpro.com
"""
# Replies to posts inherently directed to list or original sender?
DEFAULT_REPLY_GOES_TO_LIST = 0
# Admin approval unnecessary for subscribes?
DEFAULT_OPEN_SUBSCRIBE = 1
# Private_roster == 0: anyone can see, 1: members only, 2: admin only.
DEFAULT_PRIVATE_ROSTER = 0
# When exposing members, make them unrecognizable as email addrs.  To
# web-spiders from picking up addrs for spamming.
DEFAULT_OBSCURE_ADDRESSES = 1
# Make it 1 when it works.
DEFAULT_MEMBER_POSTING_ONLY = 0
# 1 for email subscription verification, 2 for admin confirmation:
DEFAULT_WEB_SUBSCRIBE_REQUIRES_CONFIRMATION = 1

		     # Digestification Defaults #

# Will list be available in non-digested form?
DEFAULT_NONDIGESTABLE = 1
# Will list be available in digested form?
DEFAULT_DIGESTABLE = 1
DEFAULT_DIGEST_HEADER = ""
DEFAULT_DIGEST_FOOTER = DEFAULT_MSG_FOOTER

DEFAULT_DIGEST_IS_DEFAULT = 0
DEFAULT_MIME_IS_DEFAULT_DIGEST = 1
DEFAULT_DIGEST_SIZE_THRESHHOLD = 30	# KB
DEFAULT_DIGEST_SEND_PERIODIC = 1
# We're only retaining the text file, an external pipermail (andrew's
# newest version) is pointed at the retained text copies.
## # 0 = never, 1 = daily, 2 = hourly:
## DEFAULT_ARCHIVE_UPDATE_FREQUENCY = 2
## # 0 = yearly, 1 = monthly
## DEFAULT_ARCHIVE_VOLUME_FREQUENCY = 0
## # Retain a flat text mailbox of postings as well as the fancy archives?
## DEFAULT_ARCHIVE_RETAIN_TEXT_COPY = 1

		    # Bounce Processing Defaults #

# Should we do any bounced mail checking at all?
DEFAULT_BOUNCE_PROCESSING = 1
# Minimum number of days that address has been undeliverable before 
# we consider nuking it..
DEFAULT_MINIMUM_REMOVAL_DATE = 5
# Minimum number of bounced posts to the list before we consider nuking it.
DEFAULT_MINIMUM_POST_COUNT_BEFORE_BOUNCE_ACTION = 3
# 0 means do nothing
# 1 means disable and send admin a report,
# 2 means nuke'em (remove) and send admin a report,
# 3 means nuke 'em and don't report (whee:)
DEFAULT_AUTOMATIC_BOUNCE_ACTION = 1
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
DisableMime         = 8 # Digesters only
ConcealSubscription = 16
