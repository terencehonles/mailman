# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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


"""Handle passwords and sanitize approved messages."""

# There are current 5 roles defined in Mailman, as codified in Defaults.py:
# user, list-creator, list-moderator, list-admin, site-admin.
#
# Here's how we do cookie based authentication.
#
# Each role (see above) has an associated password, which is currently the
# only way to authenticate a role (in the future, we'll authenticate a
# user and assign users to roles).
#
# Each cookie has the following ingredients: the authorization context's
# secret (i.e. the password, and a timestamp.  We generate an SHA1 hex
# digest of these ingredients, which we call the `mac'.  We then marshal
# up a tuple of the timestamp and the mac, hexlify that and return that as
# a cookie keyed off the authcontext.  Note that authenticating the user
# also requires the user's email address to be included in the cookie.
#
# The verification process is done in CheckCookie() below.  It extracts
# the cookie, unhexlifies and unmarshals the tuple, extracting the
# timestamp.  Using this, and the shared secret, the mac is calculated,
# and it must match the mac passed in the cookie.  If so, they're golden,
# otherwise, access is denied.
#
# It is still possible for an adversary to attempt to brute force crack
# the password if they obtain the cookie, since they can extract the
# timestamp and create macs based on password guesses.  They never get a
# cleartext version of the password though, so security rests on the
# difficulty and expense of retrying the cgi dialog for each attempt.  It
# also relies on the security of SHA1.


import os
import time
import sha
import marshal
import binascii
from types import StringType, TupleType
from urlparse import urlparse

try:
    import crypt
except ImportError:
    crypt = None

from Mailman import Errors
from Mailman import Utils
from Mailman import Cookie
from Mailman import mm_cfg



class SecurityManager:
    def InitVars(self, crypted_password):
	# Configurable, however we don't pass these back in GetConfigInfo
	# because it's a special case as it requires confirmation to change.
	self.password = crypted_password
        self.mod_password = None
	# Non configurable
	self.passwords = {}

    def AuthContextInfo(self, authcontext, user):
        # authcontext may be one of AuthUser, AuthListModerator,
        # AuthListAdmin, AuthSiteAdmin.  Not supported is the AuthCreator
        # context.
        #
        # user is ignored unless authcontext is AuthUser
        #
        # Return the authcontext's secret and cookie key.  If the authcontext
        # doesn't exist, return the tuple (None, None).  If authcontext is
        # AuthUser, but the user isn't a member of this mailing list, raise a
        # MMNotAMemberError error.  If the user's secret is None, raise a
        # MMBadUserError.
        key = self.internal_name() + ':'
        if authcontext == mm_cfg.AuthUser:
            if user is None:
                # A bad system error
                raise TypeError, 'No user supplied for AuthUser context'
            addr = self.FindUser(user)
            if addr is None:
                raise Errors.MMNotAMemberError
            secret = self.passwords.get(addr)
            if secret is None:
                raise Errors.MMBadUserError
            key += 'user:%s' % addr
        elif authcontext == mm_cfg.AuthListModerator:
            secret = self.mod_password
            key += 'moderator'
        elif authcontext == mm_cfg.AuthListAdmin:
            secret = self.password
            key += 'admin'
        # BAW: AuthCreator
        elif authcontext == mm_cfg.AuthSiteAdmin:
            # BAW: this should probably hand out a site password based cookie,
            # but that makes me a bit nervous, so just treat site admin as a
            # list admin since there is currently no site admin-only
            # functionality.
            secret = self.password
            key += 'admin'
        else:
            return None, None
        return key, secret

    def Authenticate(self, authcontexts, response, user=None):
        # Given a list of authentication contexts, check to see if the
        # response matches one of the passwords.  authcontexts must be a
        # sequence, and if it contains the context AuthUser, then the user
        # argument must not be None.
        #
        # Return the authcontext from the argument sequence that matches the
        # response, or UnAuthorized.
        for ac in authcontexts:
            if ac == mm_cfg.AuthCreator:
                ok = Utils.check_global_password(response, siteadmin=0)
                if ok:
                    return mm_cfg.AuthCreator
            elif ac == mm_cfg.AuthSiteAdmin:
                ok = Utils.check_global_password(response)
                if ok:
                    return mm_cfg.AuthSiteAdmin
            else:
                # The password for the list admin and list moderator are not
                # kept as plain text, but instead as an sha hexdigest.  The
                # response being passed in is plain text, so we need to
                # digestify it first.
                if ac in (mm_cfg.AuthListAdmin, mm_cfg.AuthListModerator):
                    chkresponse = sha.new(response).hexdigest()
                else:
                    chkresponse = response

                key, secret = self.AuthContextInfo(ac, user)
                if secret is not None and chkresponse == secret:
                    return ac
        return mm_cfg.UnAuthorized

    def WebAuthenticate(self, authcontexts, response, user=None):
        # Given a list of authentication contexts, check to see if the cookie
        # contains a matching authorization, falling back to checking whether
        # the response matches one of the passwords.  authcontexts must be a
        # sequence, and if it contains the context AuthUser, then the user
        # argument must not be None.
        #
        # Returns a flag indicating whether authentication succeeded or not.
        try:
            for ac in authcontexts:
                ok = self.CheckCookie(ac, user)
                if ok:
                    return 1
            # Check passwords
            ac = self.Authenticate(authcontexts, response, user)
            if ac:
                print self.MakeCookie(ac, user)
                return 1
        except Errors.MMNotAMemberError:
            pass
        return 0

    def MakeCookie(self, authcontext, user=None):
        key, secret = self.AuthContextInfo(authcontext, user)
        if key is None or secret is None:
            raise MMBadUserError
        # Timestamp
        issued = int(time.time())
        # Get a digest of the secret, plus other information.
        mac = sha.new(secret + `issued`).hexdigest()
        # Create the cookie object.  The way the cookie module converts
        # non-strings to pickles can cause problems if the resulting string
        # needs to be quoted.  So we'll do the conversion ourselves.
        c = Cookie.Cookie()
        c[key] = binascii.hexlify(marshal.dumps((issued, mac)))
        # The path to all Mailman stuff, minus the scheme and host,
        # i.e. usually the string `/mailman'
        path = urlparse(self.web_page_url)[2]
        c[key]['path'] = path
        # We use session cookies, so don't set `expires' or `max-age' keys.
        # Set the RFC 2109 required header.
        c[key]['version'] = 1
        return c

    def ZapCookie(self, authcontext, user=None):
        # We can throw away the secret.
        key, secret = self.AuthContextInfo(authcontext, user)
        # Logout of the session by zapping the cookie.  For safety both set
        # max-age=0 (as per RFC2109) and set the cookie data to the empty
        # string.
        c = Cookie.Cookie()
        c[key] = ''
        # The path to all Mailman stuff, minus the scheme and host,
        # i.e. usually the string `/mailman'
        path = urlparse(self.web_page_url)[2]
        c[key]['path'] = path
        c[key]['max-age'] = 0
        # Don't set expires=0 here otherwise it'll force a persistent cookie
        c[key]['version'] = 1
        return c

    def CheckCookie(self, authcontext, user=None):
        # Two results can occur: we return 1 meaning the cookie authentication
        # succeeded for the authorization context, we return 0 meaning the
        # authentication failed.
        key, secret = self.AuthContextInfo(authcontext, user)
        # Dig out the cookie data, which better be passed on this cgi
        # environment variable.  If there's no cookie data, we reject the
        # authentication.
        cookiedata = os.environ.get('HTTP_COOKIE')
        if not cookiedata:
            return 0
        c = Cookie.Cookie(cookiedata)
        if not c.has_key(key):
            return 0
        # Undo the encoding we performed in MakeCookie() above
        try:
            data = marshal.loads(binascii.unhexlify(c[key].value))
            issued, received_mac = data
        except (EOFError, ValueError, TypeError):
            return 0
        # Make sure the issued timestamp makes sense
        now = time.time()
        if now < issued:
            return 0
        # Calculate what the mac ought to be based on the cookie's timestamp
        # and the shared secret.
        mac = sha.new(secret + `issued`).hexdigest()
        if mac <> received_mac:
            return 0
        # Authenticated!
        return 1

    def ConfirmUserPassword(self, user, pw):
        """True if password is valid for site, list admin, or specific user."""
        if self.ValidAdminPassword(pw):
            return 1
        if user is None:
            raise Errors.MMBadUserError
        addr = self.FindUser(user)
        if addr is None:
            raise Errors.MMNotAMemberError
        storedpw = self.passwords.get(addr)
        if storedpw is None:
            raise Errors.MMBadUserError
        if storedpw <> pw:
            raise Errors.MMBadPasswordError
        return 1

    def ChangeUserPassword(self, user, newpw, confirm):
	addr = self.FindUser(user)
	if not addr:
	    raise Errors.MMNotAMemberError
	if newpw <> confirm:
	    raise Errors.MMPasswordsMustMatch
	self.passwords[addr] = newpw
