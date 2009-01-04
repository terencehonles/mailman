# Copyright (C) 1998-2009 by the Free Software Foundation, Inc.
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

"""Distributed default settings for significant Mailman config variables."""

from datetime import timedelta

from mailman.interfaces.mailinglist import ReplyToMunging



class CompatibleTimeDelta(timedelta):
    def __float__(self):
        # Convert to float seconds.
        return (self.days * 24 * 60 * 60 +
                self.seconds + self.microseconds / 1.0e6)

    def __int__(self):
        return int(float(self))


def seconds(s):
    return CompatibleTimeDelta(seconds=s)

def minutes(m):
    return CompatibleTimeDelta(minutes=m)

def hours(h):
    return CompatibleTimeDelta(hours=h)

def days(d):
    return CompatibleTimeDelta(days=d)


# Some convenient constants
Yes = yes = On = on = True
No = no = Off = off = False



#####
# General system-wide defaults
#####

# Should image logos be used?  Set this to 0 to disable image logos from "our
# sponsors" and just use textual links instead (this will also disable the
# shortcut "favicon").  Otherwise, this should contain the URL base path to
# the logo images (and must contain the trailing slash)..  If you want to
# disable Mailman's logo footer altogther, hack
# mailman/htmlformat.py:MailmanLogo(), which also contains the hardcoded links
# and image names.
IMAGE_LOGOS = '/icons/'

# The name of the Mailman favicon
SHORTCUT_ICON = 'mm-icon.png'

# Don't change MAILMAN_URL, unless you want to point it at one of the mirrors.
MAILMAN_URL = 'http://www.gnu.org/software/mailman/index.html'
#MAILMAN_URL = 'http://www.list.org/'
#MAILMAN_URL = 'http://mailman.sf.net/'

DEFAULT_URL_PATTERN = 'http://%s/mailman/'

# This address is used as the from address whenever a message comes from some
# entity to which there is no natural reply recipient.  Set this to a real
# human or to /dev/null.  It will be appended with the hostname of the list
# involved or the DEFAULT_EMAIL_HOST if none is available.  Address must not
# bounce and it must not point to a Mailman process.
NO_REPLY_ADDRESS = 'noreply'

# This address is the "site owner" address.  Certain messages which must be
# delivered to a human, but which can't be delivered to a list owner (e.g. a
# bounce from a list owner), will be sent to this address.  It should point to
# a human.
SITE_OWNER_ADDRESS = 'changeme@example.com'

# Normally when a site administrator authenticates to a web page with the site
# password, they get a cookie which authorizes them as the list admin.  It
# makes me nervous to hand out site auth cookies because if this cookie is
# cracked or intercepted, the intruder will have access to every list on the
# site.  OTOH, it's dang handy to not have to re-authenticate to every list on
# the site.  Set this value to Yes to allow site admin cookies.
ALLOW_SITE_ADMIN_COOKIES = No

# Command that is used to convert text/html parts into plain text.  This
# should output results to standard output.  %(filename)s will contain the
# name of the temporary file that the program should operate on.
HTML_TO_PLAIN_TEXT_COMMAND = '/usr/bin/lynx -dump %(filename)s'

# Default password hashing scheme.  See 'bin/mmsitepass -P' for a list of
# available schemes.
PASSWORD_SCHEME = 'ssha'

# Default run-time directory.
DEFAULT_VAR_DIRECTORY = '/var/mailman'



#####
# Database options
#####

# Use this to set the SQLAlchemy database engine URL.  You generally have one
# primary database connection for all of Mailman.  List data and most rosters
# will store their data in this database, although external rosters may access
# other databases in their own way.  This string support substitutions using
# any variable in the Configuration object.
DEFAULT_DATABASE_URL = 'sqlite:///$DATA_DIR/mailman.db'



#####
# Spam avoidance defaults
#####

# This variable contains a list of tuple of the format:
#
#   (header, pattern[, chain])
#
# which is used to match against the current message's headers.  If the
# pattern matches the given header in the current message, then the named
# chain is jumped to.  header is case-insensitive and should not include the
# trailing colon.  pattern is always matched with re.IGNORECASE.  chain is
# optional; if not given the 'hold' chain is used, but if given it may be any
# existing chain, such as 'discard', 'reject', or 'accept'.
#
# Note that the more searching done, the slower the whole process gets.
# Header matching is run against all messages coming to either the list, or
# the -owners address, unless the message is explicitly approved.
HEADER_MATCHES = []



#####
# Web UI defaults
#####

# Almost all the colors used in Mailman's web interface are parameterized via
# the following variables.  This lets you easily change the color schemes for
# your preferences without having to do major surgery on the source code.
# Note that in general, the template colors are not included here since it is
# easy enough to override the default template colors via site-wide,
# vdomain-wide, or list-wide specializations.

WEB_BG_COLOR = 'white'                            # Page background
WEB_HEADER_COLOR = '#99ccff'                      # Major section headers
WEB_SUBHEADER_COLOR = '#fff0d0'                   # Minor section headers
WEB_ADMINITEM_COLOR = '#dddddd'                   # Option field background
WEB_ADMINPW_COLOR = '#99cccc'                     # Password box color
WEB_ERROR_COLOR = 'red'                           # Error message foreground
WEB_LINK_COLOR = ''                               # If true, forces LINK=
WEB_ALINK_COLOR = ''                              # If true, forces ALINK=
WEB_VLINK_COLOR = ''                              # If true, forces VLINK=
WEB_HIGHLIGHT_COLOR = '#dddddd'                   # If true, alternating rows
                                                  # in listinfo & admin display
# CGI file extension.
CGIEXT = ''



#####
# Archive defaults
#####

# The url template for the public archives.  This will be used in several
# places, including the List-Archive: header, links to the archive on the
# list's listinfo page, and on the list's admin page.
#
# This variable supports several substitution variables
# - $hostname       -- the host on which the archive resides
# - $listname       -- the short name of the list being accessed
# - $fqdn_listname  -- the long name of the list being accessed
PUBLIC_ARCHIVE_URL = 'http://$hostname/pipermail/$fqdn_listname'

# The public Mail-Archive.com service's base url.
MAIL_ARCHIVE_BASEURL = 'http://go.mail-archive.com/'
# The posting address for the Mail-Archive.com service
MAIL_ARCHIVE_RECIPIENT = 'archive@mail-archive.com'

# The command for archiving to a local MHonArc instance.
MHONARC_COMMAND = """\
/usr/bin/mhonarc \
-add \
-dbfile $PRIVATE_ARCHIVE_FILE_DIR/${listname}.mbox/mhonarc.db \
-outdir $VAR_DIR/mhonarc/${listname} \
-stderr $LOG_DIR/mhonarc \
-stdout $LOG_DIR/mhonarc \
-spammode \
-umask 022"""

# Are archives on or off by default?
DEFAULT_ARCHIVE = On

# Are archives public or private by default?
# 0=public, 1=private
DEFAULT_ARCHIVE_PRIVATE = 0

# ARCHIVE_TO_MBOX
#-1 - do not do any archiving
# 0 - do not archive to mbox, use builtin mailman html archiving only
# 1 - do not use builtin mailman html archiving, archive to mbox only
# 2 - archive to both mbox and builtin mailman html archiving.
#     See the settings below for PUBLIC_EXTERNAL_ARCHIVER and
#     PRIVATE_EXTERNAL_ARCHIVER which can be used to replace mailman's
#     builtin html archiving with an external archiver.  The flat mail
#     mbox file can be useful for searching, and is another way to
#     interface external archivers, etc.
ARCHIVE_TO_MBOX = 2

# 0 - yearly
# 1 - monthly
# 2 - quarterly
# 3 - weekly
# 4 - daily
DEFAULT_ARCHIVE_VOLUME_FREQUENCY = 1
DEFAULT_DIGEST_VOLUME_FREQUENCY = 1

# These variables control the use of an external archiver.  Normally if
# archiving is turned on (see ARCHIVE_TO_MBOX above and the list's archive*
# attributes) the internal Pipermail archiver is used.  This is the default if
# both of these variables are set to No.  When either is set, the value should
# be a shell command string which will get passed to os.popen().  This string
# can contain the following substitution strings:
#
#     $listname -- gets the internal name of the list
#     $hostname -- gets the email hostname for the list
#
# being archived will be substituted for this.  Please note that os.popen() is
# used.
#
# Note that if you set one of these variables, you should set both of them
# (they can be the same string).  This will mean your external archiver will
# be used regardless of whether public or private archives are selected.
PUBLIC_EXTERNAL_ARCHIVER = No
PRIVATE_EXTERNAL_ARCHIVER = No

# A filter module that converts from multipart messages to "flat" messages
# (i.e. containing a single payload).  This is required for Pipermail, and you
# may want to set it to 0 for external archivers.  You can also replace it
# with your own module as long as it contains a process() function that takes
# a MailList object and a Message object.  It should raise
# Errors.DiscardMessage if it wants to throw the message away.  Otherwise it
# should modify the Message object as necessary.
ARCHIVE_SCRUBBER = 'mailman.pipeline.scrubber'

# Control parameter whether mailman.Handlers.Scrubber should use message
# attachment's filename as is indicated by the filename parameter or use
# 'attachement-xxx' instead.  The default is set True because the applications
# on PC and Mac begin to use longer non-ascii filenames.  Historically, it
# was set False in 2.1.6 for backward compatiblity but it was reset to True
# for safer operation in mailman-2.1.7.
SCRUBBER_DONT_USE_ATTACHMENT_FILENAME = True

# Use of attachment filename extension per se is may be dangerous because
# virus fakes it. You can set this True if you filter the attachment by
# filename extension
SCRUBBER_USE_ATTACHMENT_FILENAME_EXTENSION = False

# This variable defines what happens to text/html subparts.  They can be
# stripped completely, escaped, or filtered through an external program.  The
# legal values are:
# 0 - Strip out text/html parts completely, leaving a notice of the removal in
#     the message.  If the outer part is text/html, the entire message is
#     discarded.
# 1 - Remove any embedded text/html parts, leaving them as HTML-escaped
#     attachments which can be separately viewed.  Outer text/html parts are
#     simply HTML-escaped.
# 2 - Leave it inline, but HTML-escape it
# 3 - Remove text/html as attachments but don't HTML-escape them. Note: this
#     is very dangerous because it essentially means anybody can send an HTML
#     email to your site containing evil JavaScript or web bugs, or other
#     nasty things, and folks viewing your archives will be susceptible.  You
#     should only consider this option if you do heavy moderation of your list
#     postings.
#
# Note: given the current archiving code, it is not possible to leave
# text/html parts inline and un-escaped.  I wouldn't think it'd be a good idea
# to do anyway.
#
# The value can also be a string, in which case it is the name of a command to
# filter the HTML page through.  The resulting output is left in an attachment
# or as the entirety of the message when the outer part is text/html.  The
# format of the string must include a "%(filename)s" which will contain the
# name of the temporary file that the program should operate on.  It should
# write the processed message to stdout.  Set this to
# HTML_TO_PLAIN_TEXT_COMMAND to specify an HTML to plain text conversion
# program.
ARCHIVE_HTML_SANITIZER = 1

# Set this to Yes to enable gzipping of the downloadable archive .txt file.
# Note that this is /extremely/ inefficient, so an alternative is to just
# collect the messages in the associated .txt file and run a cron job every
# night to generate the txt.gz file.  See cron/nightly_gzip for details.
GZIP_ARCHIVE_TXT_FILES = No

# This sets the default `clobber date' policy for the archiver.  When a
# message is to be archived either by Pipermail or an external archiver,
# Mailman can modify the Date: header to be the date the message was received
# instead of the Date: in the original message.  This is useful if you
# typically receive messages with outrageous dates.  Set this to 0 to retain
# the date of the original message, or to 1 to always clobber the date.  Set
# it to 2 to perform `smart overrides' on the date; when the date is outside
# ARCHIVER_ALLOWABLE_SANE_DATE_SKEW (either too early or too late), then the
# received date is substituted instead.
ARCHIVER_CLOBBER_DATE_POLICY = 2
ARCHIVER_ALLOWABLE_SANE_DATE_SKEW = days(15)

# Pipermail archives contain the raw email addresses of the posting authors.
# Some view this as a goldmine for spam harvesters.  Set this to Yes to
# moderately obscure email addresses, but note that this breaks mailto: URLs
# in the archives too.
ARCHIVER_OBSCURES_EMAILADDRS = Yes

# Pipermail assumes that messages bodies contain US-ASCII text.
# Change this option to define a different character set to be used as
# the default character set for the archive.  The term "character set"
# is used in MIME to refer to a method of converting a sequence of
# octets into a sequence of characters.  If you change the default
# charset, you might need to add it to VERBATIM_ENCODING below.
DEFAULT_CHARSET = None

# Most character set encodings require special HTML entity characters to be
# quoted, otherwise they won't look right in the Pipermail archives.  However
# some character sets must not quote these characters so that they can be
# rendered properly in the browsers.  The primary issue is multi-byte
# encodings where the octet 0x26 does not always represent the & character.
# This variable contains a list of such characters sets which are not
# HTML-quoted in the archives.
VERBATIM_ENCODING = ['iso-2022-jp']

# When the archive is public, should Mailman also make the raw Unix mbox file
# publically available?
PUBLIC_MBOX = No



#####
# Delivery defaults
#####

# Final delivery module for outgoing mail.  This handler is used for message
# delivery to the list via the smtpd, and to an individual user.  This value
# must be a string naming an IHandler.
DELIVERY_MODULE = 'smtp-direct'

# MTA should name a module in mailman/MTA which provides the MTA specific
# functionality for creating and removing lists.  Some MTAs like Exim can be
# configured to automatically recognize new lists, in which case the MTA
# variable should be set to None.  Use 'Manual' to print new aliases to
# standard out (or send an email to the site list owner) for manual twiddling
# of an /etc/aliases style file.  Use 'Postfix' if you are using the Postfix
# MTA -- but then also see POSTFIX_STYLE_VIRTUAL_DOMAINS.
MTA = 'Manual'

# If you set MTA='Postfix', then you also want to set the following variable,
# depending on whether you're using virtual domains in Postfix, and which
# style of virtual domain you're using.  Set this to the empty list if you're
# not using virtual domains in Postfix, or if you're using Sendmail-style
# virtual domains (where all addresses are visible in all domains).  If you're
# using Postfix-style virtual domains, where aliases should only show up in
# the virtual domain, set this variable to the list of host_name values to
# write separate virtual entries for.  I.e. if you run dom1.ain, dom2.ain, and
# dom3.ain, but only dom2 and dom3 are virtual, set this variable to the list
# ['dom2.ain', 'dom3.ain'].  Matches are done against the host_name attribute
# of the mailing lists.  See the Postfix section of the installation manual
# for details.
POSTFIX_STYLE_VIRTUAL_DOMAINS = []

# We should use a separator in place of '@' for list-etc@dom2.ain in both
# aliases and mailman-virtual files.
POSTFIX_VIRTUAL_SEPARATOR = '_at_'

# These variables describe the program to use for regenerating the aliases.db
# and virtual-mailman.db files, respectively, from the associated plain text
# files.  The file being updated will be appended to this string (with a
# separating space), so it must be appropriate for os.system().
POSTFIX_ALIAS_CMD = '/usr/sbin/postalias'
POSTFIX_MAP_CMD = '/usr/sbin/postmap'

# Ceiling on the number of recipients that can be specified in a single SMTP
# transaction.  Set to 0 to submit the entire recipient list in one
# transaction.  Only used with the SMTPDirect DELIVERY_MODULE.
SMTP_MAX_RCPTS = 500

# Ceiling on the number of SMTP sessions to perform on a single socket
# connection.  Some MTAs have limits.  Set this to 0 to do as many as we like
# (i.e. your MTA has no limits).  Set this to some number great than 0 and
# Mailman will close the SMTP connection and re-open it after this number of
# consecutive sessions.
SMTP_MAX_SESSIONS_PER_CONNECTION = 0

# Maximum number of simultaneous subthreads that will be used for SMTP
# delivery.  After the recipients list is chunked according to SMTP_MAX_RCPTS,
# each chunk is handed off to the smptd by a separate such thread.  If your
# Python interpreter was not built for threads, this feature is disabled.  You
# can explicitly disable it in all cases by setting MAX_DELIVERY_THREADS to
# 0.  This feature is only supported with the SMTPDirect DELIVERY_MODULE.
#
# NOTE: This is an experimental feature and limited testing shows that it may
# in fact degrade performance, possibly due to Python's global interpreter
# lock.  Use with caution.
MAX_DELIVERY_THREADS = 0

# SMTP host and port, when DELIVERY_MODULE is 'SMTPDirect'.  Make sure the
# host exists and is resolvable (i.e., if it's the default of "localhost" be
# sure there's a localhost entry in your /etc/hosts file!)
SMTPHOST = 'localhost'
SMTPPORT = 0                                      # default from smtplib

# Command for direct command pipe delivery to sendmail compatible program,
# when DELIVERY_MODULE is 'Sendmail'.
SENDMAIL_CMD = '/usr/lib/sendmail'

# Set these variables if you need to authenticate to your NNTP server for
# Usenet posting or reading.  If no authentication is necessary, specify None
# for both variables.
NNTP_USERNAME = None
NNTP_PASSWORD = None

# Set this if you have an NNTP server you prefer gatewayed lists to use.
DEFAULT_NNTP_HOST = u''

# These variables controls how headers must be cleansed in order to be
# accepted by your NNTP server.  Some servers like INN reject messages
# containing prohibited headers, or duplicate headers.  The NNTP server may
# reject the message for other reasons, but there's little that can be
# programmatically done about that.  See mailman/Queue/NewsRunner.py
#
# First, these headers (case ignored) are removed from the original message.
NNTP_REMOVE_HEADERS = ['nntp-posting-host', 'nntp-posting-date', 'x-trace',
                       'x-complaints-to', 'xref', 'date-received', 'posted',
                       'posting-version', 'relay-version', 'received']

# Next, these headers are left alone, unless there are duplicates in the
# original message.  Any second and subsequent headers are rewritten to the
# second named header (case preserved).
NNTP_REWRITE_DUPLICATE_HEADERS = [
    ('To', 'X-Original-To'),
    ('CC', 'X-Original-CC'),
    ('Content-Transfer-Encoding', 'X-Original-Content-Transfer-Encoding'),
    ('MIME-Version', 'X-MIME-Version'),
    ]

# Some list posts and mail to the -owner address may contain DomainKey or
# DomainKeys Identified Mail (DKIM) signature headers <http://www.dkim.org/>.
# Various list transformations to the message such as adding a list header or
# footer or scrubbing attachments or even reply-to munging can break these
# signatures.  It is generally felt that these signatures have value, even if
# broken and even if the outgoing message is resigned.  However, some sites
# may wish to remove these headers by setting this to Yes.
REMOVE_DKIM_HEADERS = No

# This is the pipeline which messages sent to the -owner address go through
OWNER_PIPELINE = [
    'SpamDetect',
    'Replybot',
    'CleanseDKIM',
    'OwnerRecips',
    'ToOutgoing',
    ]


# This defines a logging subsystem confirmation file, which overrides the
# default log settings.  This is a ConfigParser formatted file which can
# contain sections named after the logger name (without the leading 'mailman.'
# common prefix).  Each section may contain the following options:
#
# - level     -- Overrides the default level; this may be any of the
#                standard Python logging levels, case insensitive.
# - format    -- Overrides the default format string; see below.
# - datefmt   -- Overrides the default date format string; see below.
# - path      -- Overrides the default logger path.  This may be a relative
#                path name, in which case it is relative to Mailman's LOG_DIR,
#                or it may be an absolute path name.  You cannot change the
#                handler class that will be used.
# - propagate -- Boolean specifying whether to propagate log message from this
#                logger to the root "mailman" logger.  You cannot override
#                settings for the root logger.
#
# The file name may be absolute, or relative to Mailman's etc directory.
LOG_CONFIG_FILE = None

# This defines log format strings for the SMTPDirect delivery module (see
# DELIVERY_MODULE above).  Valid %()s string substitutions include:
#
#     time -- the time in float seconds that it took to complete the smtp
#     hand-off of the message from Mailman to your smtpd.
#
#     size -- the size of the entire message, in bytes
#
#     #recips -- the number of actual recipients for this message.
#
#     #refused -- the number of smtp refused recipients (use this only in
#     SMTP_LOG_REFUSED).
#
#     listname -- the `internal' name of the mailing list for this posting
#
#     msg_<header> -- the value of the delivered message's given header.  If
#     the message had no such header, then "n/a" will be used.  Note though
#     that if the message had multiple such headers, then it is undefined
#     which will be used.
#
#     allmsg_<header> - Same as msg_<header> above, but if there are multiple
#     such headers in the message, they will all be printed, separated by
#     comma-space.
#
#     sender -- the "sender" of the messages, which will be the From: or
#     envelope-sender as determeined by the USE_ENVELOPE_SENDER variable
#     below.
#
# The format of the entries is a 2-tuple with the first element naming the
# logger (as a child of the root 'mailman' logger) to print the message to,
# and the second being a format string appropriate for Python's %-style string
# interpolation.  The file name is arbitrary; qfiles/<name> will be created
# automatically if it does not exist.

# The format of the message printed for every delivered message, regardless of
# whether the delivery was successful or not.  Set to None to disable the
# printing of this log message.
SMTP_LOG_EVERY_MESSAGE = (
    'smtp',
    ('${message-id} smtp to $listname for ${#recips} recips, '
     'completed in $time seconds'))

# This will only be printed if there were no immediate smtp failures.
# Mutually exclusive with SMTP_LOG_REFUSED.
SMTP_LOG_SUCCESS = (
    'post',
    '${message-id} post to $listname from $sender, size=$size, success')

# This will only be printed if there were any addresses which encountered an
# immediate smtp failure.  Mutually exclusive with SMTP_LOG_SUCCESS.
SMTP_LOG_REFUSED = (
    'post',
    ('${message-id} post to $listname from $sender, size=$size, '
     '${#refused} failures'))

# This will be logged for each specific recipient failure.  Additional %()s
# keys are:
#
#     recipient -- the failing recipient address
#     failcode  -- the smtp failure code
#     failmsg   -- the actual smtp message, if available
SMTP_LOG_EACH_FAILURE = (
    'smtp-failure',
    ('${message-id} delivery to $recipient failed with code $failcode: '
     '$failmsg'))

# These variables control the format and frequency of VERP-like delivery for
# better bounce detection.  VERP is Variable Envelope Return Path, defined
# here:
#
# http://cr.yp.to/proto/verp.txt
#
# This involves encoding the address of the recipient as we (Mailman) know it
# into the envelope sender address (i.e. the SMTP `MAIL FROM:' address).
# Thus, no matter what kind of forwarding the recipient has in place, should
# it eventually bounce, we will receive an unambiguous notice of the bouncing
# address.
#
# However, we're technically only "VERP-like" because we're doing the envelope
# sender encoding in Mailman, not in the MTA.  We do require cooperation from
# the MTA, so you must be sure your MTA can be configured for extended address
# semantics.
#
# The first variable describes how to encode VERP envelopes.  It must contain
# these three string interpolations:
#
# %(bounces)s -- the list-bounces mailbox will be set here
# %(mailbox)s -- the recipient's mailbox will be set here
# %(host)s    -- the recipient's host name will be set here
#
# This example uses the default below.
#
# FQDN list address is: mylist@dom.ain
# Recipient is:         aperson@a.nother.dom
#
# The envelope sender will be mylist-bounces+aperson=a.nother.dom@dom.ain
#
# Note that your MTA /must/ be configured to deliver such an addressed message
# to mylist-bounces!
VERP_DELIMITER = '+'
VERP_FORMAT = '%(bounces)s+%(mailbox)s=%(host)s'

# The second describes a regular expression to unambiguously decode such an
# address, which will be placed in the To: header of the bounce message by the
# bouncing MTA.  Getting this right is critical -- and tricky.  Learn your
# Python regular expressions.  It must define exactly three named groups,
# bounces, mailbox and host, with the same definition as above.  It will be
# compiled case-insensitively.
VERP_REGEXP = r'^(?P<bounces>[^+]+?)\+(?P<mailbox>[^=]+)=(?P<host>[^@]+)@.*$'

# VERP format and regexp for probe messages
VERP_PROBE_FORMAT = '%(bounces)s+%(token)s'
VERP_PROBE_REGEXP = r'^(?P<bounces>[^+]+?)\+(?P<token>[^@]+)@.*$'
# Set this Yes to activate VERP probe for disabling by bounce
VERP_PROBES = No

# A perfect opportunity for doing VERP is the password reminders, which are
# already addressed individually to each recipient.  Set this to Yes to enable
# VERPs on all password reminders.
VERP_PASSWORD_REMINDERS = No

# Another good opportunity is when regular delivery is personalized.  Here
# again, we're already incurring the performance hit for addressing each
# individual recipient.  Set this to Yes to enable VERPs on all personalized
# regular deliveries (personalized digests aren't supported yet).
VERP_PERSONALIZED_DELIVERIES = No

# And finally, we can VERP normal, non-personalized deliveries.  However,
# because it can be a significant performance hit, we allow you to decide how
# often to VERP regular deliveries.  This is the interval, in number of
# messages, to do a VERP recipient address.  The same variable controls both
# regular and digest deliveries.  Set to 0 to disable occasional VERPs, set to
# 1 to VERP every delivery, or to some number > 1 for only occasional VERPs.
VERP_DELIVERY_INTERVAL = 0

# For nicer confirmation emails, use a VERP-like format which encodes the
# confirmation cookie in the reply address.  This lets us put a more user
# friendly Subject: on the message, but requires cooperation from the MTA.
# Format is like VERP_FORMAT above, but with the following substitutions:
#
# $address  -- the list-confirm address
# $cookie   -- the confirmation cookie
VERP_CONFIRM_FORMAT = '$address+$cookie'

# This is analogous to VERP_REGEXP, but for splitting apart the
# VERP_CONFIRM_FORMAT.  MUAs have been observed that mung
# From: local_part@host
# into
# To: "local_part" <local_part@host>
# when replying, so we skip everything up to '<' if any.
VERP_CONFIRM_REGEXP = r'^(.*<)?(?P<addr>[^+]+?)\+(?P<cookie>[^@]+)@.*$'

# Set this to Yes to enable VERP-like (more user friendly) confirmations
VERP_CONFIRMATIONS = No

# This is the maximum number of automatic responses sent to an address because
# of -request messages or posting hold messages.  This limit prevents response
# loops between Mailman and misconfigured remote email robots.  Mailman
# already inhibits automatic replies to any message labeled with a header
# "Precendence: bulk|list|junk".  This is a fallback safety valve so it should
# be set fairly high.  Set to 0 for no limit (probably useful only for
# debugging).
MAX_AUTORESPONSES_PER_DAY = 10



#####
# Qrunner defaults
#####

# Which queues should the qrunner master watchdog spawn?  add_qrunner() takes
# one required argument, which is the name of the qrunner to start
# (capitalized and without the 'Runner' suffix).  Optional second argument
# specifies the number of parallel processes to fork for each qrunner.  If
# more than one process is used, each will take an equal subdivision of the
# hash space, so the number must be a power of 2.
#
# del_qrunners() takes one argument which is the name of the qrunner not to
# start.  This is used because by default, Mailman starts the Arch, Bounce,
# Command, Incoming, News, Outgoing, Retry, and Virgin queues.
#
# Set this to Yes to use the `Maildir' delivery option.  If you change this
# you will need to re-run bin/genaliases for MTAs that don't use list
# auto-detection.
#
# WARNING: If you want to use Maildir delivery, you /must/ start Mailman's
# qrunner as root, or you will get permission problems.
USE_MAILDIR = No

# Set this to Yes to use the `LMTP' delivery option.  If you change this
# you will need to re-run bin/genaliases for MTAs that don't use list
# auto-detection.
#
# You have to set following line in postfix main.cf:
#     transport_maps = hash:<prefix>/data/transport
# Also needed is following line if your list is in $mydestination:
#     alias_maps = hash:/etc/aliases, hash:<prefix>/data/aliases
USE_LMTP = No

# Name of the domains which operate on LMTP Mailman only.  Currently valid
# only for Postfix alias generation.
LMTP_ONLY_DOMAINS = []

# If the list is not present in LMTP_ONLY_DOMAINS, LMTPRunner would return
# 550 response to the master SMTP agent.  This may cause 'bounce spam relay'
# in that a spammer expects to deliver the message as bounce info to the
# 'From:' address.  You can override this behavior by setting
# LMTP_ERR_550 = '250 Ok. But, blackholed because mailbox unavailable'.
LMTP_ERR_550 = '550 Requested action not taken: mailbox unavailable'

# WSGI Server.
#
# You must enable PROXY of Apache httpd server and configure to pass Mailman
# CGI requests to this WSGI Server:
#
#     ProxyPass /mailman/ http://localhost:2580/mailman/
#
# Note that local URI part should be the same.
# XXX If you are running Apache 2.2, you will probably also want to set
# ProxyPassReverseCookiePath
#
# Also you have to add following line to <prefix>/etc/mailman.cfg
# add_qrunner('HTTP')
HTTP_HOST = 'localhost'
HTTP_PORT = 2580

# After processing every file in the qrunner's slice, how long should the
# runner sleep for before checking the queue directory again for new files?
# This can be a fraction of a second, or zero to check immediately
# (essentially busy-loop as fast as possible).
QRUNNER_SLEEP_TIME = seconds(1)

# When a message that is unparsable (by the email package) is received, what
# should we do with it?  The most common cause of unparsable messages is
# broken MIME encapsulation, and the most common cause of that is viruses like
# Nimda.  Set this variable to No to discard such messages, or to Yes to store
# them in qfiles/bad subdirectory.
QRUNNER_SAVE_BAD_MESSAGES = Yes

# This flag causes Mailman to fsync() its data files after writing and
# flushing its contents.  While this ensures the data is written to disk,
# avoiding data loss, it may be a performance killer.  Note that this flag
# affects both message pickles and MailList config.pck files.
SYNC_AFTER_WRITE = No

# The maximum number of times that the mailmanctl watcher will try to restart
# a qrunner that exits uncleanly.
MAX_RESTARTS = 10



#####
# General defaults
#####

# The default language for this server.  Whenever we can't figure out the list
# context or user context, we'll fall back to using this language.  This code
# must be in the list of available language codes.
DEFAULT_SERVER_LANGUAGE = u'en'

# When allowing only members to post to a mailing list, how is the sender of
# the message determined?  If this variable is set to Yes, then first the
# message's envelope sender is used, with a fallback to the sender if there is
# no envelope sender.  Set this variable to No to always use the sender.
#
# The envelope sender is set by the SMTP delivery and is thus less easily
# spoofed than the sender, which is typically just taken from the From: header
# and thus easily spoofed by the end-user.  However, sometimes the envelope
# sender isn't set correctly and this will manifest itself by postings being
# held for approval even if they appear to come from a list member.  If you
# are having this problem, set this variable to No, but understand that some
# spoofed messages may get through.
USE_ENVELOPE_SENDER = No

# Membership tests for posting purposes are usually performed by looking at a
# set of headers, passing the test if any of their values match a member of
# the list.  Headers are checked in the order given in this variable.  The
# value None means use the From_ (envelope sender) header.  Field names are
# case insensitive.
SENDER_HEADERS = ('from', None, 'reply-to', 'sender')

# How many members to display at a time on the admin cgi to unsubscribe them
# or change their options?
DEFAULT_ADMIN_MEMBER_CHUNKSIZE = 30

# how many bytes of a held message post should be displayed in the admindb web
# page?  Use a negative number to indicate the entire message, regardless of
# size (though this will slow down rendering those pages).
ADMINDB_PAGE_TEXT_LIMIT = 4096

# Set this variable to Yes to allow list owners to delete their own mailing
# lists.  You may not want to give them this power, in which case, setting
# this variable to No instead requires list removal to be done by the site
# administrator, via the command line script bin/rmlist.
OWNERS_CAN_DELETE_THEIR_OWN_LISTS = No

# Set this variable to Yes to allow list owners to set the "personalized"
# flags on their mailing lists.  Turning these on tells Mailman to send
# separate email messages to each user instead of batching them together for
# delivery to the MTA.  This gives each member a more personalized message,
# but can have a heavy impact on the performance of your system.
OWNERS_CAN_ENABLE_PERSONALIZATION = No

# Should held messages be saved on disk as Python pickles or as plain text?
# The former is more efficient since we don't need to go through the
# parse/generate roundtrip each time, but the latter might be preferred if you
# want to edit the held message on disk.
HOLD_MESSAGES_AS_PICKLES = Yes

# This variable controls the order in which list-specific category options are
# presented in the admin cgi page.
ADMIN_CATEGORIES = [
    # First column
    'general', 'passwords', 'language', 'members', 'nondigest', 'digest',
    # Second column
    'privacy', 'bounce', 'archive', 'gateway', 'autoreply',
    'contentfilter', 'topics',
    ]

# See "Bitfield for user options" below; make this a sum of those options, to
# make all new members of lists start with those options flagged.  We assume
# by default that people don't want to receive two copies of posts.  Note
# however that the member moderation flag's initial value is controlled by the
# list's config variable default_member_moderation.
DEFAULT_NEW_MEMBER_OPTIONS = 256

# Specify the type of passwords to use, when Mailman generates the passwords
# itself, as would be the case for membership requests where the user did not
# fill in a password, or during list creation, when auto-generation of admin
# passwords was selected.
#
# Set this value to Yes for classic Mailman user-friendly(er) passwords.
# These generate semi-pronounceable passwords which are easier to remember.
# Set this value to No to use more cryptographically secure, but harder to
# remember, passwords -- if your operating system and Python version support
# the necessary feature (specifically that /dev/urandom be available).
USER_FRIENDLY_PASSWORDS = Yes
# This value specifies the default lengths of member and list admin passwords
MEMBER_PASSWORD_LENGTH = 8
ADMIN_PASSWORD_LENGTH = 10



#####
# List defaults.  NOTE: Changing these values does NOT change the
# configuration of an existing list.  It only defines the default for new
# lists you subsequently create.
#####

# Should a list, by default be advertised?  What is the default maximum number
# of explicit recipients allowed?  What is the default maximum message size
# allowed?
DEFAULT_LIST_ADVERTISED = Yes
DEFAULT_MAX_NUM_RECIPIENTS = 10
DEFAULT_MAX_MESSAGE_SIZE = 40           # KB

# These format strings will be expanded w.r.t. the dictionary for the
# mailing list instance.
DEFAULT_SUBJECT_PREFIX  = u'[$mlist.real_name] '
# DEFAULT_SUBJECT_PREFIX = "[$mlist.real_name %%d]" # for numbering
DEFAULT_MSG_HEADER = u''
DEFAULT_MSG_FOOTER = u"""\
_______________________________________________
$real_name mailing list
$fqdn_listname
${listinfo_page}
"""

# Scrub regular delivery
DEFAULT_SCRUB_NONDIGEST = False

# Mail command processor will ignore mail command lines after designated max.
EMAIL_COMMANDS_MAX_LINES = 10

# Is the list owner notified of admin requests immediately by mail, as well as
# by daily pending-request reminder?
DEFAULT_ADMIN_IMMED_NOTIFY = Yes

# Is the list owner notified of subscribes/unsubscribes?
DEFAULT_ADMIN_NOTIFY_MCHANGES = No

# Discard held messages after this days
DEFAULT_MAX_DAYS_TO_HOLD = 0

# Should list members, by default, have their posts be moderated?
DEFAULT_DEFAULT_MEMBER_MODERATION = No

# Should non-member posts which are auto-discarded also be forwarded to the
# moderators?
DEFAULT_FORWARD_AUTO_DISCARDS = Yes

# What shold happen to non-member posts which are do not match explicit
# non-member actions?
# 0 = Accept
# 1 = Hold
# 2 = Reject
# 3 = Discard
DEFAULT_GENERIC_NONMEMBER_ACTION = 1

# Bounce if 'To:', 'Cc:', or 'Resent-To:' fields don't explicitly name list?
# This is an anti-spam measure
DEFAULT_REQUIRE_EXPLICIT_DESTINATION = Yes

# Alternate names acceptable as explicit destinations for this list.
DEFAULT_ACCEPTABLE_ALIASES = """
"""
# For mailing lists that have only other mailing lists for members:
DEFAULT_UMBRELLA_LIST = No

# For umbrella lists, the suffix for the account part of address for
# administrative notices (subscription confirmations, password reminders):
DEFAULT_UMBRELLA_MEMBER_ADMIN_SUFFIX = "-owner"

# This variable controls whether monthly password reminders are sent.
DEFAULT_SEND_REMINDERS = Yes

# Send welcome messages to new users?
DEFAULT_SEND_WELCOME_MSG = Yes

# Send goodbye messages to unsubscribed members?
DEFAULT_SEND_GOODBYE_MSG = Yes

# Wipe sender information, and make it look like the list-admin
# address sends all messages
DEFAULT_ANONYMOUS_LIST = No

# {header-name: regexp} spam filtering - we include some for example sake.
DEFAULT_BOUNCE_MATCHING_HEADERS = u"""
# Lines that *start* with a '#' are comments.
to: friend@public.com
message-id: relay.comanche.denmark.eu
from: list@listme.com
from: .*@uplinkpro.com
"""

# Mailman can be configured to "munge" Reply-To: headers for any passing
# messages.  One the one hand, there are a lot of good reasons not to munge
# Reply-To: but on the other, people really seem to want this feature.  See
# the help for reply_goes_to_list in the web UI for links discussing the
# issue.
# 0 - Reply-To: not munged
# 1 - Reply-To: set back to the list
# 2 - Reply-To: set to an explicit value (reply_to_address)
DEFAULT_REPLY_GOES_TO_LIST = ReplyToMunging.no_munging

# Mailman can be configured to strip any existing Reply-To: header, or simply
# extend any existing Reply-To: with one based on the above setting.
DEFAULT_FIRST_STRIP_REPLY_TO = No

# SUBSCRIBE POLICY
# 0 - open list (only when ALLOW_OPEN_SUBSCRIBE is set to 1) **
# 1 - confirmation required for subscribes
# 2 - admin approval required for subscribes
# 3 - both confirmation and admin approval required
#
# ** please do not choose option 0 if you are not allowing open
# subscribes (next variable)
DEFAULT_SUBSCRIBE_POLICY = 1

# Does this site allow completely unchecked subscriptions?
ALLOW_OPEN_SUBSCRIBE = No

# This is the default list of addresses and regular expressions (beginning
# with ^) that are exempt from approval if SUBSCRIBE_POLICY is 2 or 3.
DEFAULT_SUBSCRIBE_AUTO_APPROVAL = []

# The default policy for unsubscriptions.  0 (unmoderated unsubscribes) is
# highly recommended!
# 0 - unmoderated unsubscribes
# 1 - unsubscribes require approval
DEFAULT_UNSUBSCRIBE_POLICY = 0

# Private_roster == 0: anyone can see, 1: members only, 2: admin only.
DEFAULT_PRIVATE_ROSTER = 1

# When exposing members, make them unrecognizable as email addrs, so
# web-spiders can't pick up addrs for spam purposes.
DEFAULT_OBSCURE_ADDRESSES = Yes

# RFC 2369 defines List-* headers which are added to every message sent
# through to the mailing list membership.  These are a very useful aid to end
# users and should always be added.  However, not all MUAs are compliant and
# if a list's membership has many such users, they may clamor for these
# headers to be suppressed.  By setting this variable to Yes, list owners will
# be given the option to suppress these headers.  By setting it to No, list
# owners will not be given the option to suppress these headers (although some
# header suppression may still take place, i.e. for announce-only lists, or
# lists with no archives).
ALLOW_RFC2369_OVERRIDES = Yes

# Defaults for content filtering on mailing lists.  DEFAULT_FILTER_CONTENT is
# a flag which if set to true, turns on content filtering.
DEFAULT_FILTER_CONTENT = No

# DEFAULT_FILTER_MIME_TYPES is a list of MIME types to be removed.  This is a
# list of strings of the format "maintype/subtype" or simply "maintype".
# E.g. "text/html" strips all html attachments while "image" strips all image
# types regardless of subtype (jpeg, gif, etc.).
DEFAULT_FILTER_MIME_TYPES = []

# DEFAULT_PASS_MIME_TYPES is a list of MIME types to be passed through.
# Format is the same as DEFAULT_FILTER_MIME_TYPES
DEFAULT_PASS_MIME_TYPES = ['multipart/mixed',
                           'multipart/alternative',
                           'text/plain']

# DEFAULT_FILTER_FILENAME_EXTENSIONS is a list of filename extensions to be
# removed. It is useful because many viruses fake their content-type as
# harmless ones while keep their extension as executable and expect to be
# executed when victims 'open' them.
DEFAULT_FILTER_FILENAME_EXTENSIONS = [
    'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'cpl'
    ]

# DEFAULT_PASS_FILENAME_EXTENSIONS is a list of filename extensions to be
# passed through. Format is the same as DEFAULT_FILTER_FILENAME_EXTENSIONS.
DEFAULT_PASS_FILENAME_EXTENSIONS = []

# Replace multipart/alternative with its first alternative.
DEFAULT_COLLAPSE_ALTERNATIVES = Yes

# Whether text/html should be converted to text/plain after content filtering
# is performed.  Conversion is done according to HTML_TO_PLAIN_TEXT_COMMAND
DEFAULT_CONVERT_HTML_TO_PLAINTEXT = Yes

# Default action to take on filtered messages.
# 0 = Discard, 1 = Reject, 2 = Forward, 3 = Preserve
DEFAULT_FILTER_ACTION = 0

# Whether to allow list owners to preserve content filtered messages to a
# special queue on the disk.
OWNERS_CAN_PRESERVE_FILTERED_MESSAGES = Yes

# Check for administrivia in messages sent to the main list?
DEFAULT_ADMINISTRIVIA = Yes



#####
# Digestification defaults.  Same caveat applies here as with list defaults.
#####

# Will list be available in non-digested form?
DEFAULT_NONDIGESTABLE = Yes

# Will list be available in digested form?
DEFAULT_DIGESTABLE = Yes
DEFAULT_DIGEST_HEADER = u''
DEFAULT_DIGEST_FOOTER = DEFAULT_MSG_FOOTER

DEFAULT_DIGEST_IS_DEFAULT = No
DEFAULT_MIME_IS_DEFAULT_DIGEST = No
DEFAULT_DIGEST_SIZE_THRESHOLD = 30     # KB
DEFAULT_DIGEST_SEND_PERIODIC = Yes

# Headers which should be kept in both RFC 1153 (plain) and MIME digests.  RFC
# 1153 also specifies these headers in this exact order, so order matters.
MIME_DIGEST_KEEP_HEADERS = [
    'Date', 'From', 'To', 'Cc', 'Subject', 'Message-ID', 'Keywords',
    # I believe we should also keep these headers though.
    'In-Reply-To', 'References', 'Content-Type', 'MIME-Version',
    'Content-Transfer-Encoding', 'Precedence', 'Reply-To',
    # Mailman 2.0 adds these headers
    'Message',
    ]

PLAIN_DIGEST_KEEP_HEADERS = [
    'Message', 'Date', 'From',
    'Subject', 'To', 'Cc',
    'Message-ID', 'Keywords',
    'Content-Type',
    ]



#####
# Bounce processing defaults.  Same caveat applies here as with list defaults.
#####

# Should we do any bounced mail response at all?
DEFAULT_BOUNCE_PROCESSING = Yes

# How often should the bounce qrunner process queued detected bounces?
REGISTER_BOUNCES_EVERY = minutes(15)

# Bounce processing works like this: when a bounce from a member is received,
# we look up the `bounce info' for this member. If there is no bounce info,
# this is the first bounce we've received from this member.  In that case, we
# record today's date, and initialize the bounce score (see below for initial
# value).
#
# If there is existing bounce info for this member, we look at the last bounce
# receive date.  If this date is farther away from today than the `bounce
# expiration interval', we throw away all the old data and initialize the
# bounce score as if this were the first bounce from the member.
#
# Otherwise, we increment the bounce score.  If we can determine whether the
# bounce was soft or hard (i.e. transient or fatal), then we use a score value
# of 0.5 for soft bounces and 1.0 for hard bounces.  Note that we only score
# one bounce per day.  If the bounce score is then greater than the `bounce
# threshold' we disable the member's address.
#
# After disabling the address, we can send warning messages to the member,
# providing a confirmation cookie/url for them to use to re-enable their
# delivery.  After a configurable period of time, we'll delete the address.
# When we delete the address due to bouncing, we'll send one last message to
# the member.

# Bounce scores greater than this value get disabled.
DEFAULT_BOUNCE_SCORE_THRESHOLD = 5.0

# Bounce information older than this interval is considered stale, and is
# discarded.
DEFAULT_BOUNCE_INFO_STALE_AFTER = days(7)

# The number of notifications to send to the disabled/removed member before we
# remove them from the list.  A value of 0 means we remove the address
# immediately (with one last notification).  Note that the first one is sent
# upon change of status to disabled.
DEFAULT_BOUNCE_YOU_ARE_DISABLED_WARNINGS = 3

# The interval of time between disabled warnings.
DEFAULT_BOUNCE_YOU_ARE_DISABLED_WARNINGS_INTERVAL = days(7)

# Does the list owner get messages to the -bounces (and -admin) address that
# failed to match by the bounce detector?
DEFAULT_BOUNCE_UNRECOGNIZED_GOES_TO_LIST_OWNER = Yes

# Notifications on bounce actions.  The first specifies whether the list owner
# should get a notification when a member is disabled due to bouncing, while
# the second specifies whether the owner should get one when the member is
# removed due to bouncing.
DEFAULT_BOUNCE_NOTIFY_OWNER_ON_DISABLE = Yes
DEFAULT_BOUNCE_NOTIFY_OWNER_ON_REMOVAL = Yes



#####
# General time limits
#####

# Default length of time a pending request is live before it is evicted from
# the pending database.
PENDING_REQUEST_LIFE = days(3)

# How long should messages which have delivery failures continue to be
# retried?  After this period of time, a message that has failed recipients
# will be dequeued and those recipients will never receive the message.
DELIVERY_RETRY_PERIOD = days(5)

# How long should we wait before we retry a temporary delivery failure?
DELIVERY_RETRY_WAIT = hours(1)



#####
# Lock management defaults
#####

# These variables control certain aspects of lock acquisition and retention.
# They should be tuned as appropriate for your environment.  All variables are
# specified in units of floating point seconds.  YOU MAY NEED TO TUNE THESE
# VARIABLES DEPENDING ON THE SIZE OF YOUR LISTS, THE PERFORMANCE OF YOUR
# HARDWARE, NETWORK AND GENERAL MAIL HANDLING CAPABILITIES, ETC.

# This variable specifies how long the lock will be retained for a specific
# operation on a mailing list.  Watch your logs/lock file and if you see a lot
# of lock breakages, you might need to bump this up.  However if you set this
# too high, a faulty script (or incorrect use of bin/withlist) can prevent the
# list from being used until the lifetime expires.  This is probably one of
# the most crucial tuning variables in the system.
LIST_LOCK_LIFETIME = hours(5)

# This variable specifies how long an attempt will be made to acquire a list
# lock by the incoming qrunner process.  If the lock acquisition times out,
# the message will be re-queued for later delivery.
LIST_LOCK_TIMEOUT = seconds(10)

# Set this to On to turn on lock debugging messages for the pending requests
# database, which will be written to logs/locks.  If you think you're having
# lock problems, or just want to tune the locks for your system, turn on lock
# debugging.
PENDINGDB_LOCK_DEBUGGING = Off



#####
# Nothing below here is user configurable.  Most of these values are in this
# file for internal system convenience.  Don't change any of them or override
# any of them in your mailman.cfg file!
#####

# Enumeration for Mailman cgi widget types
Toggle      = 1
Radio       = 2
String      = 3
Text        = 4
Email       = 5
EmailList   = 6
Host        = 7
Number      = 8
FileUpload  = 9
Select      = 10
Topics      = 11
Checkbox    = 12
# An "extended email list".  Contents must be an email address or a ^-prefixed
# regular expression.  Used in the sender moderation text boxes.
EmailListEx = 13
# Extended spam filter widget
HeaderFilter  = 14

# Actions
DEFER = 0
APPROVE = 1
REJECT = 2
DISCARD = 3
SUBSCRIBE = 4
UNSUBSCRIBE = 5
ACCEPT = 6
HOLD = 7

# Standard text field width
TEXTFIELDWIDTH = 40

# Bitfield for user options.  See DEFAULT_NEW_MEMBER_OPTIONS above to set
# defaults for all new lists.
Digests             = 0 # handled by other mechanism, doesn't need a flag.
DisableDelivery     = 1 # Obsolete; use set/getDeliveryStatus()
DontReceiveOwnPosts = 2 # Non-digesters only
AcknowledgePosts    = 4
DisableMime         = 8 # Digesters only
ConcealSubscription = 16
SuppressPasswordReminder = 32
ReceiveNonmatchingTopics = 64
Moderate = 128
DontReceiveDuplicates = 256


# A mapping between short option tags and their flag
OPTINFO = {'hide'    : ConcealSubscription,
           'nomail'  : DisableDelivery,
           'ack'     : AcknowledgePosts,
           'notmetoo': DontReceiveOwnPosts,
           'digest'  : 0,
           'plain'   : DisableMime,
           'nodupes' : DontReceiveDuplicates
           }

# Authentication contexts.
#
# Mailman defines the following roles:

# - User, a normal user who has no permissions except to change their personal
#   option settings
# - List creator, someone who can create and delete lists, but cannot
#   (necessarily) configure the list.
# - List moderator, someone who can tend to pending requests such as
#   subscription requests, or held messages
# - List administrator, someone who has total control over a list, can
#   configure it, modify user options for members of the list, subscribe and
#   unsubscribe members, etc.
# - Site administrator, someone who has total control over the entire site and
#   can do any of the tasks mentioned above.  This person usually also has
#   command line access.

UnAuthorized = 0
AuthUser = 1          # Joe Shmoe User
AuthCreator = 2       # List Creator / Destroyer
AuthListAdmin = 3     # List Administrator (total control over list)
AuthListModerator = 4 # List Moderator (can only handle held requests)
AuthSiteAdmin = 5     # Site Administrator (total control over everything)



# Vgg: Language descriptions and charsets dictionary, any new supported
# language must have a corresponding entry here. Key is the name of the
# directories that hold the localized texts. Data are tuples with first
# element being the description, as described in the catalogs, and second
# element is the language charset.  I have chosen code from /usr/share/locale
# in my GNU/Linux. :-)
#
# TK: Now the site admin can select languages for the installation from those
# in the distribution tarball.  We don't touch add_language() function for
# backward compatibility.  You may have to add your own language in your
# mailman.cfg file, if it is not included in the distribution even if you had
# put language files in source directory and configured by `--with-languages'
# option.
def _(s):
    return s

_DEFAULT_LANGUAGE_DATA = {
    'ar':       (_('Arabic'),               'utf-8'),
    'ca':       (_('Catalan'),              'iso-8859-1'),
    'cs':       (_('Czech'),                'iso-8859-2'),
    'da':       (_('Danish'),               'iso-8859-1'),
    'de':       (_('German'),               'iso-8859-1'),
    'en':       (_('English (USA)'),        'us-ascii'),
    'es':       (_('Spanish (Spain)'),      'iso-8859-1'),
    'et':       (_('Estonian'),             'iso-8859-15'),
    'eu':       (_('Euskara'),              'iso-8859-15'), # Basque
    'fi':       (_('Finnish'),              'iso-8859-1'),
    'fr':       (_('French'),               'iso-8859-1'),
    'hr':       (_('Croatian'),             'iso-8859-2'),
    'hu':       (_('Hungarian'),            'iso-8859-2'),
    'ia':       (_('Interlingua'),          'iso-8859-15'),
    'it':       (_('Italian'),              'iso-8859-1'),
    'ja':       (_('Japanese'),             'euc-jp'),
    'ko':       (_('Korean'),               'euc-kr'),
    'lt':       (_('Lithuanian'),           'iso-8859-13'),
    'nl':       (_('Dutch'),                'iso-8859-1'),
    'no':       (_('Norwegian'),            'iso-8859-1'),
    'pl':       (_('Polish'),               'iso-8859-2'),
    'pt':       (_('Portuguese'),           'iso-8859-1'),
    'pt_BR':    (_('Portuguese (Brazil)'),  'iso-8859-1'),
    'ro':       (_('Romanian'),             'iso-8859-2'),
    'ru':       (_('Russian'),              'koi8-r'),
    'sr':       (_('Serbian'),              'utf-8'),
    'sl':       (_('Slovenian'),            'iso-8859-2'),
    'sv':       (_('Swedish'),              'iso-8859-1'),
    'tr':       (_('Turkish'),              'iso-8859-9'),
    'uk':       (_('Ukrainian'),            'utf-8'),
    'vi':       (_('Vietnamese'),           'utf-8'),
    'zh_CN':    (_('Chinese (China)'),      'utf-8'),
    'zh_TW':    (_('Chinese (Taiwan)'),     'utf-8'),
}


del _
