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

"""Process subscription or roster requests from listinfo form."""

import sys
import os
import cgi
import signal

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman import i18n
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog

SLASH = '/'

# Set up i18n
_ = i18n._
i18n.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)



def main():
    doc = Document()
    doc.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)

    parts = Utils.GetPathPieces()
    if not parts:
        doc.AddItem(Header(2, _("Error")))
        doc.AddItem(Bold(_('Invalid options to CGI script')))
        print doc.Format(bgcolor="#ffffff")
        return
        
    listname = parts[0].lower()
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        doc.AddItem(Header(2, _("Error")))
        doc.AddItem(Bold(_('No such list <em>%(listname)s</em>')))
        print doc.Format(bgcolor="#ffffff")
        syslog('error', 'No such list "%s": %s\n' % (listname, e))
        return

    # See if the form data has a preferred language set, in which case, use it
    # for the results.  If not, use the list's preferred language.
    cgidata = cgi.FieldStorage()
    if cgidata.has_key('language'):
        language = cgidata['language'].value
    else:
        language = mlist.preferred_language

    i18n.set_language(language)
    doc.set_language(language)

    # We need a signal handler to catch the SIGTERM that can come from Apache
    # when the user hits the browser's STOP button.  See the comment in
    # admin.py for details.
    #
    # BAW: Strictly speaking, the list should not need to be locked just to
    # read the request database.  However the request database asserts that
    # the list is locked in order to load it and it's not worth complicating
    # that logic.
    def sigterm_handler(signum, frame, mlist=mlist):
        # Make sure the list gets unlocked...
        mlist.Unlock()
        # ...and ensure we exit, otherwise race conditions could cause us to
        # enter MailList.Save() while we're in the unlocked state, and that
        # could be bad!
        sys.exit(0)

    mlist.Lock()
    try:
        # Install the emergency shutdown signal handler
        signal.signal(signal.SIGTERM, sigterm_handler)

        process_form(mlist, doc, cgidata, language)
        mlist.Save()
    finally:
        mlist.Unlock()



def call_script(mlist, member, which):
    """A hack to call one of the other CGI scripts."""
    os.environ['PATH_INFO'] = SLASH.join([mlist.internal_name(), member])
    pkg = __import__('Mailman.Cgi', globals(), locals(), [which])
    mod = getattr(pkg, which)
    mlist.Save()
    mlist.Unlock()
    mod.main()
    sys.stdout.flush()
    sys.stderr.flush()
    # skip finally clause above since we've already saved and unlocked the list
    os._exit(0)



def process_form(mlist, doc, cgidata, lang):
    error = 0
    results = ''

    if cgidata.has_key('UserOptions') or \
            cgidata.has_key('info') and \
            not cgidata.has_key("email"):
        # Then go to user options section.
        if not cgidata.has_key('info'):
            doc.AddItem(Header(2, _("Error")))
            doc.AddItem(Bold(_("You must supply your email address.")))
            doc.AddItem(mlist.GetMailmanFooter())
            print doc.Format(bgcolor="#ffffff")
            return

        addr = cgidata['info'].value
        member = mlist.FindUser(addr)
        if not member:
            realname = mlist.real_name
            doc.AddItem(Header(2, _("Error")))
            doc.AddItem(Bold(
                _("%(realname)s has no subscribed addr <i>%(addr)s</i>.")))
            doc.AddItem(mlist.GetMailmanFooter())
            print doc.Format(bgcolor="#ffffff")
            return

        call_script(mlist, member, 'options')
        # should never get here!
        assert 0

    if not cgidata.has_key('email'):
        error = 1
        results += _("You must supply a valid email address.<br>")
        # define email so we don't get a NameError below
        # with if email == mlist.GetListEmail() -scott
        email = ''
    else:
        email = cgidata['email'].value

    remote = remote_addr()
    if email == mlist.GetListEmail():
        error = 1
        if remote:
            remote = _("Web site ") + remote
        else:
            remote = _("unidentified origin")
        badremote = "\n\tfrom " + remote
        syslog("mischief", "Attempt to self subscribe %s:%s"
               % (email, badremote))
        results += _('You must not subscribe a list to itself!<br>')

    # If the user did not supply a password, generate one for him
    if cgidata.has_key('pw'):
        password = cgidata['pw'].value
    else:
        password = None
    if cgidata.has_key('pw-conf'):
        confirmed = cgidata['pw-conf'].value
    else:
        confirmed = None

    if password is None and confirmed is None:
        password = Utils.MakeRandomPassword()
    elif password is None or confirmed is None:
        error = 1
        results += _('If you supply a password, you must confirm it.<br>')
    elif password <> confirmed:
        error = 1
        results += _('Your passwords did not match.<br>')

    # Get the digest option for the subscription.
    if cgidata.has_key('digest'):
        try:
            digest = int(cgidata['digest'].value)
        except ValueError:
            # TBD: Hmm, this shouldn't happen
            digest = 0
    else:
        digest = mlist.digest_is_default

    if not mlist.digestable:
        digest = 0
    elif not mlist.nondigestable:
        digest = 1

    if not error:
        try:
            if mlist.FindUser(email):
                raise Errors.MMAlreadyAMember, email

            mlist.AddMember(email, password, digest, remote, lang)
        #
        # check for all the errors that mlist.AddMember can throw
        # options  on the web page for this cgi
        #
        except Errors.MMBadEmailError:
            results += (_("Mailman won't accept the given email "
                          "address as a valid address. (Does it "
                          "have an @ in it???)<p>"))
        except Errors.MMListError:
            results += (_("The list is not fully functional, and "
                          "can not accept subscription requests.<p>"))
        except Errors.MMSubscribeNeedsConfirmation:
             results += (_("Confirmation from your email address is "
                           "required, to prevent anyone from "
                           "subscribing you without permission. "
                           "Instructions are being "
                           "sent to you at %(email)s. Please note your "
                           "subscription will not start until you "
                           "confirm your subscription."))

        except Errors.MMNeedApproval, x:
            # We need to interpolate into x
            realname = mlist.real_name
            x = _(x)
            results += (_("Subscription was <em>deferred</em> "
                          "because %(x)s.  Your request has been "
                          "forwarded to the list administrator.  "
                          "You will receive email informing you "
                          "of the moderator's decision when they "
                          "get to your request.<p>"))
        except Errors.MMHostileAddress:
            results += (_("Your subscription is not allowed because "
                          "the email address you gave is insecure.<p>"))
        except Errors.MMAlreadyAMember:
            results += _("You are already subscribed!<p>")
        #
        # these shouldn't happen, but if someone's futzing with the cgi
        # they might -scott
        #
        except Errors.MMCantDigestError:
            results += _("No one can subscribe to the digest of this list!")
        except Errors.MMMustDigestError:
            results += _("This list only supports digest subscriptions!")
        else:
            rname = mlist.real_name
            results += _("You have been successfully subscribed to %(rname)s.")
    # Show the results
    print_results(mlist, results, doc, lang)



def print_results(mlist, results, doc, lang):
    replacements = mlist.GetStandardReplacements(lang)
    replacements['<mm-results>'] = results
    output = mlist.ParseTags('subscribe.html', replacements, lang)
    doc.AddItem(output)
    print doc.Format(bgcolor="#ffffff")



def remote_addr():
    "Try to return the remote addr, or if unavailable, None."
    if os.environ.has_key('REMOTE_HOST'):
        return os.environ['REMOTE_HOST']
    elif os.environ.has_key('REMOTE_ADDR'):
        return os.environ['REMOTE_ADDR']
    else:
        return None
