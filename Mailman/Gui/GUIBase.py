# Copyright (C) 2002-2008 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Base class for all web GUI components."""

import re

from Mailman import Defaults
from Mailman import Errors
from Mailman import Utils
from Mailman.i18n import _

NL = '\n'
BADJOINER = '</code>, <code>'



class GUIBase:
    # Providing a common interface for GUI component form processing.  Most
    # GUI components won't need to override anything, but some may want to
    # override _setValue() to provide some specialized processing for some
    # attributes.
    def _getValidValue(self, mlist, property, wtype, val):
        # Coerce and validate the new value.
        #
        # Radio buttons and boolean toggles both have integral type
        if wtype in (Defaults.Radio, Defaults.Toggle):
            # Let ValueErrors propagate
            return int(val)
        # String and Text widgets both just return their values verbatim
        # but convert into unicode (for 2.2)
        if wtype in (Defaults.String, Defaults.Text):
            return unicode(val, Utils.GetCharSet(mlist.preferred_language))
        # This widget contains a single email address
        if wtype == Defaults.Email:
            # BAW: We must allow blank values otherwise reply_to_address can't
            # be cleared.  This is currently the only Defaults.Email type
            # widget in the interface, so watch out if we ever add any new
            # ones.
            if val:
                # Let InvalidEmailAddress propagate.
                Utils.ValidateEmail(val)
            return val
        # These widget types contain lists of email addresses, one per line.
        # The EmailListEx allows each line to contain either an email address
        # or a regular expression
        if wtype in (Defaults.EmailList, Defaults.EmailListEx):
            # BAW: value might already be a list, if this is coming from
            # config_list input.  Sigh.
            if isinstance(val, list):
                return val
            addrs = []
            for addr in [s.strip() for s in val.split(NL)]:
                # Discard empty lines
                if not addr:
                    continue
                try:
                    # This throws an exception if the address is invalid
                    Utils.ValidateEmail(addr)
                except Errors.EmailAddressError:
                    # See if this is a context that accepts regular
                    # expressions, and that the re is legal
                    if wtype == Defaults.EmailListEx and addr.startswith('^'):
                        try:
                            re.compile(addr)
                        except re.error:
                            raise ValueError
                    else:
                        raise
                addrs.append(addr)
            return addrs
        # This is a host name, i.e. verbatim
        if wtype == Defaults.Host:
            return val
        # This is a number, either a float or an integer
        if wtype == Defaults.Number:
            num = -1
            try:
                num = int(val)
            except ValueError:
                # Let ValueErrors percolate up
                num = float(val)
            if num < 0:
                return getattr(mlist, property)
            return num
        # This widget is a select box, i.e. verbatim
        if wtype == Defaults.Select:
            return val
        # Checkboxes return a list of the selected items, even if only one is
        # selected.
        if wtype == Defaults.Checkbox:
            if isinstance(val, list):
                return val
            return [val]
        if wtype == Defaults.FileUpload:
            return val
        if wtype == Defaults.Topics:
            return val
        if wtype == Defaults.HeaderFilter:
            return val
        # Should never get here
        assert 0, 'Bad gui widget type: %s' % wtype

    def _setValue(self, mlist, property, val, doc):
        # Set the value, or override to take special action on the property
        if not property.startswith('_') and getattr(mlist, property) <> val:
            setattr(mlist, property, val)

    def _postValidate(self, mlist, doc):
        # Validate all the attributes for this category
        pass

    def _escape(self, property, value):
        value = value.replace('<', '&lt;')
        return value

    def handleForm(self, mlist, category, subcat, cgidata, doc):
        for item in self.GetConfigInfo(mlist, category, subcat):
            # Skip descriptions and legacy non-attributes
            if not isinstance(item, tuple) or len(item) < 5:
                continue
            # Unpack the gui item description
            property, wtype, args, deps, desc = item[0:5]
            # BAW: I know this code is a little crufty but I wanted to
            # reproduce the semantics of the original code in admin.py as
            # closely as possible, for now.  We can clean it up later.
            #
            # The property may be uploadable...
            uploadprop = property + '_upload'
            if cgidata.has_key(uploadprop) and cgidata[uploadprop].value:
                val = cgidata[uploadprop].value
            elif not cgidata.has_key(property):
                continue
            elif isinstance(cgidata[property], list):
                val = [self._escape(property, x.value)
                       for x in cgidata[property]]
            else:
                val = self._escape(property, cgidata[property].value)
            # Coerce the value to the expected type, raising exceptions if the
            # value is invalid.
            try:
                val = self._getValidValue(mlist, property, wtype, val)
            except ValueError:
                doc.addError(_('Invalid value for variable: %(property)s'))
            # This is the parent of InvalidEmailAddress
            except Errors.EmailAddressError:
                doc.addError(
                    _('Bad email address for option %(property)s: %(val)s'))
            else:
                # Set the attribute, which will normally delegate to the mlist
                self._setValue(mlist, property, val, doc)
        # Do a final sweep once all the attributes have been set.  This is how
        # we can do cross-attribute assertions
        self._postValidate(mlist, doc)

    # Convenience method for handling $-string attributes
    def _convertString(self, mlist, property, alloweds, val, doc):
        # Is the list using $-strings?
        dollarp = getattr(mlist, 'use_dollar_strings', 0)
        if dollarp:
            ids = Utils.dollar_identifiers(val)
        else:
            # %-strings
            ids = Utils.percent_identifiers(val)
        # Here's the list of allowable interpolations
        for allowed in alloweds:
            if ids.has_key(allowed):
                del ids[allowed]
        if ids:
            # What's left are not allowed
            badkeys = ids.keys()
            badkeys.sort()
            bad = BADJOINER.join(badkeys)
            doc.addError(_(
                """The following illegal substitution variables were
                found in the <code>%(property)s</code> string:
                <code>%(bad)s</code>
                <p>Your list may not operate properly until you correct this
                problem."""), tag=_('Warning: '))
            return val
        # Now if we're still using %-strings, do a roundtrip conversion and
        # see if the converted value is the same as the new value.  If not,
        # then they probably left off a trailing `s'.  We'll warn them and use
        # the corrected string.
        if not dollarp:
            fixed = Utils.to_percent(Utils.to_dollar(val))
            if fixed <> val:
                doc.addError(_(
                    """Your <code>%(property)s</code> string appeared to
                    have some correctable problems in its new value.
                    The fixed value will be used instead.  Please
                    double check that this is what you intended.
                    """))
                return fixed
        return val
