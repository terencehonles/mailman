# Copyright (C) 1998 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software 
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


"""Shared mailman errors and messages."""


# XXX: These should be converted to new style class exceptions
MMUnknownListError   = "MMUnknownListError"
MMBadListError       = "MMBadListError"
MMBadUserError       = "MMBadUserError"
MMBadConfigError     = "MMBadConfigError"

# Exception hierarchy for bad email address errors that can be raised from
# Utils.ValidateEmail()
class EmailAddressError(Exception):
    pass
class MMBadEmailError(EmailAddressError):
    pass
class MMHostileAddress(EmailAddressError):
    pass

# Exception hierarchy for various authentication failures, can be
# raised from functions in SecurityManager.py
class MMAuthenticationError(Exception): pass
class MMBadPasswordError(MMAuthenticationError): pass
class MMPasswordsMustMatch(MMAuthenticationError): pass
class MMCookieError(MMAuthenticationError): pass
class MMExpiredCookieError(MMCookieError): pass
class MMInvalidCookieError(MMCookieError): pass

MMMustDigestError    = "MMMustDigestError"
MMCantDigestError    = "MMCantDigestError"
MMNotAMemberError    = "MMNotAMemberError"
MMListNotReady       = "MMListNotReady"
MMNoSuchUserError    = "MMNoSuchUserError"
MMNeedApproval       = "MMNeedApproval"
MMSubscribeNeedsConfirmation = "MMSubscribeNeedsConfirmation"
MMBadConfirmation    = "MMBadConfirmation"
MMAlreadyAMember     = "MMAlreadyAMember"
MMAlreadyDigested    = "MMAlreadyDigested"
MMAlreadyUndigested  = "MMAlreadyUndigested"

class MMLoopingPost:
    """Post already went through this list!"""
    pass

MODERATED_LIST_MSG    = "Moderated list"
IMPLICIT_DEST_MSG     = "Implicit destination"
SUSPICIOUS_HEADER_MSG = "Suspicious header"
FORBIDDEN_SENDER_MSG  = "Forbidden sender"

# XXX: This should be converted to templates/*.txt style
MESSAGE_DECORATION_NOTE = """This text can include  <b>%(field)s</b> format
strings which are resolved against the list's attribute dictionary (__dict__).
Some useful fields are:

<dl>
  <dt>real_name
  <dd>The "pretty" name of the list, with capitalization.
  <dt>_internal_name
  <dd>The name by which the list is identified in URLs, where case
      is germane.
  <dt>host_name
  <dd>The domain-qualified host name where the list server runs.
  <dt>web_page_url
  <dd>The mailman root URL to which, eg, 'listinfo/%(_internal_name)s
      can be appended to yield the listinfo page for the list.
  <dt>description
  <dd>The brief description of the list.
  <dt>info
  <dd>The less brief list description.
</dl>
"""
