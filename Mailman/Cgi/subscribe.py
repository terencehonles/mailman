# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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
import string
import cgi

from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman.htmlformat import *
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog



def main():
    doc = Document()
    parts = Utils.GetPathPieces()
    if not parts:
        doc.AddItem(Header(2, _("Error")))
        doc.AddItem(Bold(_('Invalid options to CGI script')))
        print doc.Format(bgcolor="#ffffff")
        return
        
    listname = string.lower(parts[0])
    try:
        mlist = MailList.MailList(listname)
        mlist.IsListInitialized()
    except Errors.MMListError, e:
        doc.AddItem(Header(2, _("Error")))
        doc.AddItem(Bold(_('No such list <em>%s</em>') % listname))
        print doc.Format(bgcolor="#ffffff")
        syslog('error', 'No such list "%s": %s\n' % (listname, e))
        return

    os.environ['LANG'] = mlist.preferred_language

    try:
        process_form(mlist, doc)
    finally:
        mlist.Save()
        mlist.Unlock()



def call_script(mlist, member, which):
    """A hack to call one of the other CGI scripts."""
    os.environ['PATH_INFO'] = string.join([mlist.internal_name(), member], '/')
    pkg = __import__('Mailman.Cgi', globals(), locals(), [which])
    mod = getattr(pkg, which)
    mlist.Save()
    mlist.Unlock()
    mod.main()
    sys.stdout.flush()
    sys.stderr.flush()
    # skip finally clause above since we've already saved and unlocked the list
    os._exit(0)



def process_form(mlist, doc):
    form = cgi.FieldStorage()
    error = 0
    results = ''

    # Preliminaries done, actual processing of the form input below.
    if form.has_key("language"):
        language = form["language"].value
    else:
        language = mlist.preferred_language

    os.environ['LANG'] = language

    if form.has_key("UserOptions") or \
            form.has_key("info") and \
            not form.has_key("email"):
        # then
        # Go to user options section.
        if not form.has_key("info"):
            doc.AddItem(Header(2, _("Error")))
            doc.AddItem(Bold(_("You must supply your email address.")))
            doc.AddItem(mlist.GetMailmanFooter())
            print doc.Format(bgcolor="#ffffff")
            return

        addr = form['info'].value
        member = mlist.FindUser(addr)
        if not member:
            doc.AddItem(Header(2, _("Error")))
            doc.AddItem(Bold(_("%s has no subscribed addr <i>%s</i>.")
                             % (mlist.real_name, addr)))
            doc.AddItem(mlist.GetMailmanFooter())
            print doc.Format(bgcolor="#ffffff")
            return

        call_script(mlist, member, 'options')
        # should never get here!
        assert 0

    if not form.has_key("email"):
        error = 1
        results = results + _("You must supply a valid email address.<br>")
        #
        # define email so we don't get a NameError below
        # with if email == mlist.GetListEmail() -scott
        #
        email = ""
    else:
        email = form["email"].value

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
        results = results + _("You must not subscribe a list to itself!<br>")

    if not form.has_key("pw") or not form.has_key("pw-conf"):
        error = 1
        results = (results +
                   _("You must supply a valid password, and confirm it.<br>"))
    else:
        pw  = form["pw"].value
        pwc = form["pw-conf"].value

    if not error and pw <> pwc:
        error = 1
        results = results + _("Your passwords did not match.<br>")

    if form.has_key("digest"):
        try:
            digest = int(form['digest'].value)
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
            if digest:
                digesting = " digest"
            else:
                digesting = ""
            mlist.AddMember(email, pw, digest, remote, language)
        #
        # check for all the errors that mlist.AddMember can throw
        # options  on the web page for this cgi
        #
        except Errors.MMBadEmailError:
            results = results + (_("Mailman won't accept the given email "
                                 "address as a valid address. (Does it "
                                 "have an @ in it???)<p>"))
        except Errors.MMListError:
            results = results + (_("The list is not fully functional, and "
                                 "can not accept subscription requests.<p>"))
        except Errors.MMSubscribeNeedsConfirmation:
             results = results + (_("Confirmation from your email address is "
                                  "required, to prevent anyone from "
                                  "subscribing you without permission. "
                                  "Instructions are being "
                                  "sent to you at %s. Please note your "
                                  "subscription will not start until you "
                                  "confirm your subscription.") % email)

        except Errors.MMNeedApproval, x:
            results = results + (_("Subscription was <em>deferred</em> "
                                 "because %s.  Your request has been "
                                 "forwarded to the list administrator.  "
                                 "You will receive email informing you "
                                 "of the moderator's decision when they "
                                 "get to your request.<p>") % x)
        except Errors.MMHostileAddress:
            results = results + (_("Your subscription is not allowed because "
                                 "the email address you gave is insecure.<p>"))
        except Errors.MMAlreadyAMember:
            results = results + _("You are already subscribed!<p>")
        #
        # these shouldn't happen, but if someone's futzing with the cgi
        # they might -scott
        #
        except Errors.MMCantDigestError:
            results = results + \
                      _("No one can subscribe to the digest of this list!")
        except Errors.MMMustDigestError:
            results = results + \
                      _("This list only supports digest subscriptions!")
        else:
            results = results + \
                      _("You have been successfully subscribed to %s.") % \
                      (mlist.real_name)
    PrintResults(mlist, results, doc, language)



def PrintResults(mlist, results, doc, lang=None):
    if lang is None:
        lang = mlist.preferred_language
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
