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

"""Process input to user options form."""

import sys
import os
import string
import cgi

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog



def PrintResults(mlist, operation, doc, results, user=None):
    if user:
        url = '%s/%s' % (mlist.GetScriptURL('options'),
                         Utils.ObscureEmail(user))
        results = results + '<p>Continue to ' + \
                  Link(url, 'edit your personal options').Format() + \
                  '.'
    replacements = mlist.GetStandardReplacements()
    replacements['<mm-results>'] = results
    replacements['<mm-operation>'] = operation
    output = mlist.ParseTags('handle_opts.html', replacements)
    doc.AddItem(output)
    print doc.Format(bgcolor="#ffffff")
    # hrm...
    sys.exit(0)



def main():
    doc = Document()
    parts = Utils.GetPathPieces()
    if not parts or len(parts) < 2:
        doc.AddItem(Header(2, "Error"))
        doc.AddItem(Bold("Invalid options to CGI script."))
        print doc.Format(bgcolor="#ffffff")
        return

    listname = string.lower(parts[0])
    user = parts[1]

    try:
        mlist = MailList.MailList(listname)
    except Errors.MMListError, e:
        doc.AddItem(Header(2, "Error"))
        doc.AddItem(Bold('No such list <em>%s</em>' % listname))
        print doc.Format(bgcolor="#ffffff")
        syslog('error', 'No such list "%s": %s\n' % (listname, e))
        return

    try:
        process_form(mlist, user, doc)
    finally:
        mlist.Save()
        mlist.Unlock()



def process_form(mlist, user, doc):
    form = cgi.FieldStorage()
    error = 0
    operation = ""
    user = Utils.LCDomain(user)

    if not Utils.FindMatchingAddresses(user, mlist.members,
                                       mlist.digest_members):
        PrintResults(mlist, operation, doc, "%s not a member!<p>" % user)

    if form.has_key("unsub"):
        operation = "Unsubscribe"
        if not form.has_key("upw"):
            PrintResults(mlist, operation, doc,
                         "You must give your password to unsubscribe.<p>",
                         user)
        else:
            try:
                pw = form["upw"].value
                if mlist.ConfirmUserPassword(user, pw):
                    mlist.DeleteMember(user, "web cmd")
            except Errors.MMListNotReadyError:
                PrintResults(mlist, operation, doc, "List is not functional.",
                             user)
            except Errors.MMNoSuchUserError:
                PrintResults(mlist, operation, doc,
                             "You seem to already be not a member.<p>", user)
            except Errors.MMBadUserError:
                PrintResults(mlist, operation, doc,
                             "Your account has gone awry - "
                             "please contact the list administrator!<p>", user)
            except Errors.MMBadPasswordError:
                PrintResults(mlist, operation, doc,
                             "That password was incorrect.<p>")
        PrintResults(mlist, operation, doc, "You have been unsubscribed.<p>",
                     user)

    elif form.has_key("emailpw"):
        try:
            mlist.MailUserPassword(user)
            PrintResults(mlist, operation, doc,
                         "A reminder of your password "
                         "has been emailed to you.<p>", user)
        except Errors.MMBadUserError:
            PrintResults(mlist, operation, doc,
                         "The password entry for `%s' has not "
                         'been found.  The list administrator is being '
                         'notified.<p>' % user, user)

    elif form.has_key("othersubs"):
        if not form.has_key('othersubspw'):
            PrintResults(mlist, operation, doc,
                         "You must specify your password.", user)
        else:
            try:
                mlist.ConfirmUserPassword(user, form['othersubspw'].value)
            except Errors.MMListNotReadyError:
                PrintResults(mlist, operation, doc,
                             "The list is currently not functional.", user)
            except Errors.MMNotAMemberError:
                PrintResults(mlist, operation, doc,
                             "You seem to no longer be a list member.", user)
            except Errors.MMBadPasswordError:
                PrintResults(mlist, operation, doc, "Incorrect password.",
                             user)
            except Errors.MMBadUserError:
                PrintResults(
                    mlist, operation, doc,
                    "You have no password.  Contact the list administrator.",
                    user)

            doc.AddItem(Header(2, "List Subscriptions for %s on %s"
                               % (user, mlist.host_name)))
            doc.AddItem("Click a link to visit your options page for"
                        " that mailing list:")

            def optionslinks(listname, user=user):
                mlist = MailList.MailList(listname, lock=0)
                addrs = Utils.FindMatchingAddresses(user, mlist.members,
                                                    mlist.digest_members)
                if addrs:
                    addr = Utils.ObscureEmail(addrs[0])
                    if mlist.obscure_addresses:
                        addr = Utils.ObscureEmail(addr)
                    url = mlist.GetOptionsURL(addr)
                    link = Link(url, mlist.real_name)
                    return mlist.internal_name(), link

            all_links = filter(None, map(optionslinks, Utils.list_names()))
            all_links.sort()
            items = OrderedList()
            for name, link in all_links:
                items.AddItem(link)
            doc.AddItem(items)
            print doc.Format(bgcolor="#ffffff")

    elif form.has_key("changepw"):
        if form.has_key('opw') and \
                form.has_key('newpw') and \
                form.has_key('confpw'):
            # then
            try:
                mlist.ConfirmUserPassword(user, form['opw'].value)
                mlist.ChangeUserPassword(user, form['newpw'].value,
                                         form['confpw'].value)
            except Errors.MMListNotReadyError:
                PrintResults(mlist, operation, doc,
                             "The list is currently not functional.",
                             user)
            except Errors.MMNotAMemberError:
                PrintResults(mlist, operation, doc,
                             "You seem to no longer be a list member.",
                             user)
            except Errors.MMBadPasswordError:
                PrintResults(mlist, operation, doc,
                             "The old password you supplied was incorrect.",
                             user)
            except Errors.MMPasswordsMustMatch:
                PrintResults(mlist, operation, doc, "Passwords must match.",
                             user)

            PrintResults(mlist, operation, doc,
                         "Your password has been changed.",
                         user)
        else:
            PrintResults(mlist, operation, doc,
                         "You must specify your old password,"
                         " and your new password twice.", user)

    else:
        # if key doesn't exist, or its value can't be int()'ified, return the
        # current value (essentially a noop)
        def getval(key, default, form=form):
            if form.has_key(key):
                try:
                    return int(form[key].value)
                except ValueError:
                    return default
            return default

        useropt = mlist.GetUserOption
        digest_value = getval('digest', useropt(user, mm_cfg.Digests))
        mime = getval('mime', useropt(user, mm_cfg.DisableMime))
        dont_receive = getval('dontreceive',
                              useropt(user, mm_cfg.DontReceiveOwnPosts))
        ack_posts = getval('ackposts', useropt(user, mm_cfg.AcknowledgePosts))
        disable_mail = getval('disablemail',
                              useropt(user, mm_cfg.DisableDelivery))
        conceal = getval('conceal', useropt(user, mm_cfg.ConcealSubscription))

        if not form.has_key("digpw"):
            PrintResults(mlist, operation, doc,
                         "You must supply a password to change options.",
                         user)
        try:
            mlist.ConfirmUserPassword(user, form['digpw'].value)
        except Errors.MMAlreadyDigested:
            pass
        except Errors.MMAlreadyUndigested:
            pass
        except Errors.MMMustDigestError:
            PrintResults(mlist, operation, doc,
                         "List only accepts digest members.", user)
        except Errors.MMCantDigestError:
            PrintResults(mlist, operation, doc,
                         "List doesn't accept digest members.", user)
        except Errors.MMNotAMemberError:
            PrintResults(mlist, operation, doc,
                         "%s isn't subscribed to this list."
                         % mail.GetSender(), user)
        except Errors.MMListNotReadyError:
            PrintResults(mlist, operation, doc, "List is not functional.",
                         user)
        except Errors.MMNoSuchUserError:
            PrintResults(mlist, operation, doc,
                         "%s is not subscribed to this list."
                         % mail.GetSender(), user)
        except Errors.MMBadPasswordError:
            PrintResults(mlist, operation, doc,
                         "You gave the wrong password.", user)

        mlist.SetUserOption(user, mm_cfg.DisableDelivery, disable_mail)
        mlist.SetUserOption(user, mm_cfg.DontReceiveOwnPosts, dont_receive)
        mlist.SetUserOption(user, mm_cfg.AcknowledgePosts, ack_posts)
        mlist.SetUserOption(user, mm_cfg.DisableMime, mime)
        msg = 'You have successfully set your options.'
        try:
            mlist.SetUserDigest(user, digest_value)
            # digest mode changed from on to off, so send the current digest
            # to the user.
            if digest_value == 0:
                PrintResults(mlist, operation, doc,
                             'You may get one last digest.', user)
        except (Errors.MMAlreadyDigested, Errors.MMAlreadyUndigested):
            pass
        except Errors.MMCantDigestError:
            msg = '''The list administrator has disabled digest delivery for
            this list, so your delivery option has not been set.  However your
            other options have been set successfully.'''
        except Errors.MMMustDigestError:
            msg = '''The list administrator has disabled non-digest delivery
            for this list, so your delivery option has not been set.  However
            your other options have been set successfully.'''
        mlist.SetUserOption(user, mm_cfg.ConcealSubscription, conceal)
        PrintResults(mlist, operation, doc, msg, user)
