# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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

import re
import sys
import time
import optparse

from mailman import MailList
from mailman import errors
from mailman.configuration import config
from mailman.core.i18n import _
from mailman.initialize import initialize
from mailman.utilities.string import wrap
from mailman.version import MAILMAN_VERSION


NL = '\n'
nonasciipat = re.compile(r'[\x80-\xff]')



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] listname

Configure a list from a text file description, or dump a list's configuration
settings."""))
    parser.add_option('-i', '--inputfile',
                      metavar='FILENAME', default=None, type='string',
                      help=_("""\
Configure the list by assigning each module-global variable in the file to an
attribute on the mailing list object, then save the list.  The named file is
loaded with execfile() and must be legal Python code.  Any variable that isn't
already an attribute of the list object is ignored (a warning message is
printed).  See also the -c option.

A special variable named 'mlist' is put into the globals during the execfile,
which is bound to the actual MailList object.  This lets you do all manner of
bizarre thing to the list object, but BEWARE!  Using this can severely (and
possibly irreparably) damage your mailing list!

The may not be used with the -o option."""))
    parser.add_option('-o', '--outputfile',
                      metavar='FILENAME', default=None, type='string',
                      help=_("""\
Instead of configuring the list, print out a mailing list's configuration
variables in a format suitable for input using this script.  In this way, you
can easily capture the configuration settings for a particular list and
imprint those settings on another list.  FILENAME is the file to output the
settings to.  If FILENAME is `-', standard out is used.

This may not be used with the -i option."""))
    parser.add_option('-c', '--checkonly',
                      default=False, action='store_true', help=_("""\
With this option, the modified list is not actually changed.  This is only
useful with the -i option."""))
    parser.add_option('-v', '--verbose',
                      default=False, action='store_true', help=_("""\
Print the name of each attribute as it is being changed.  This is only useful
with the -i option."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if len(args) > 1:
        parser.print_help()
        parser.error(_('Unexpected arguments'))
    if not args:
        parser.error(_('List name is required'))
    return parser, opts, args



def do_output(listname, outfile, parser):
    closep = False
    try:
        if outfile == '-':
            outfp = sys.stdout
        else:
            outfp = open(outfile, 'w')
            closep = True
        # Open the specified list unlocked, since we're only reading it.
        try:
            mlist = MailList.MailList(listname, lock=False)
        except errors.MMListError:
            parser.error(_('No such list: $listname'))
        # Preamble for the config info. PEP 263 charset and capture time.
        charset = mlist.preferred_language.charset
        # Set the system's default language.
        _.default = mlist.preferred_language.code
        if not charset:
            charset = 'us-ascii'
        when = time.ctime(time.time())
        print >> outfp, _('''\
# -*- python -*-
# -*- coding: $charset -*-
## "$listname" mailing list configuration settings
## captured on $when
''')
        # Get all the list config info.  All this stuff is accessible via the
        # web interface.
        for k in config.ADMIN_CATEGORIES:
            subcats = mlist.GetConfigSubCategories(k)
            if subcats is None:
                do_list_categories(mlist, k, None, outfp)
            else:
                for subcat in [t[0] for t in subcats]:
                    do_list_categories(mlist, k, subcat, outfp)
    finally:
        if closep:
            outfp.close()



def do_list_categories(mlist, k, subcat, outfp):
    info = mlist.GetConfigInfo(k, subcat)
    label, gui = mlist.GetConfigCategories()[k]
    if info is None:
        return
    charset = mlist.preferred_language.charset
    print >> outfp, '##', k.capitalize(), _('options')
    print >> outfp, '#'
    # First, massage the descripton text, which could have obnoxious
    # leading whitespace on second and subsequent lines due to
    # triple-quoted string nonsense in the source code.
    desc = NL.join([s.lstrip() for s in info[0].splitlines()])
    # Print out the category description
    desc = wrap(desc)
    for line in desc.splitlines():
        print >> outfp, '#', line
    print >> outfp
    for data in info[1:]:
        if not isinstance(data, tuple):
            continue
        varname = data[0]
        # Variable could be volatile
        if varname[0] == '_':
            continue
        vtype = data[1]
        # First, massage the descripton text, which could have
        # obnoxious leading whitespace on second and subsequent lines
        # due to triple-quoted string nonsense in the source code.
        desc = NL.join([s.lstrip() for s in data[-1].splitlines()])
        # Now strip out all HTML tags
        desc = re.sub('<.*?>', '', desc)
        # And convert &lt;/&gt; to <>
        desc = re.sub('&lt;', '<', desc)
        desc = re.sub('&gt;', '>', desc)
        # Print out the variable description.
        desc = wrap(desc)
        for line in desc.split('\n'):
            print >> outfp, '#', line
        # munge the value based on its type
        value = None
        if hasattr(gui, 'getValue'):
            value = gui.getValue(mlist, vtype, varname, data[2])
        if value is None and not varname.startswith('_'):
            value = getattr(mlist, varname)
        if vtype in (config.String, config.Text, config.FileUpload):
            print >> outfp, varname, '=',
            lines = value.splitlines()
            if not lines:
                print >> outfp, "''"
            elif len(lines) == 1:
                if charset != 'us-ascii' and nonasciipat.search(lines[0]):
                    # This is more readable for non-english list.
                    print >> outfp, '"' + lines[0].replace('"', '\\"') + '"'
                else:
                    print >> outfp, repr(lines[0])
            else:
                if charset == 'us-ascii' and nonasciipat.search(value):
                    # Normally, an english list should not have non-ascii char.
                    print >> outfp, repr(NL.join(lines))
                else:
                    outfp.write(' """')
                    outfp.write(NL.join(lines).replace('"', '\\"'))
                    outfp.write('"""\n')
        elif vtype in (config.Radio, config.Toggle):
            print >> outfp, '#'
            print >> outfp, '#', _('legal values are:')
            # TBD: This is disgusting, but it's special cased
            # everywhere else anyway...
            if varname == 'subscribe_policy' and \
                   not config.ALLOW_OPEN_SUBSCRIBE:
                i = 1
            else:
                i = 0
            for choice in data[2]:
                print >> outfp, '#   ', i, '= "%s"' % choice
                i += 1
            print >> outfp, varname, '=', repr(value)
        else:
            print >> outfp, varname, '=', repr(value)
        print >> outfp



def getPropertyMap(mlist):
    guibyprop = {}
    categories = mlist.GetConfigCategories()
    for category, (label, gui) in categories.items():
        if not hasattr(gui, 'GetConfigInfo'):
            continue
        subcats = mlist.GetConfigSubCategories(category)
        if subcats is None:
            subcats = [(None, None)]
        for subcat, sclabel in subcats:
            for element in gui.GetConfigInfo(mlist, category, subcat):
                if not isinstance(element, tuple):
                    continue
                propname = element[0]
                wtype = element[1]
                guibyprop[propname] = (gui, wtype)
    return guibyprop


class FakeDoc:
    # Fake the error reporting API for the htmlformat.Document class
    def addError(self, s, tag=None, *args):
        if tag:
            print >> sys.stderr, tag
        print >> sys.stderr, s % args

    def set_language(self, val):
        pass



def do_input(listname, infile, checkonly, verbose, parser):
    fakedoc = FakeDoc()
    # Open the specified list locked, unless checkonly is set
    try:
        mlist = MailList.MailList(listname, lock=not checkonly)
    except errors.MMListError as error:
        parser.error(_('No such list "$listname"\n$error'))
    savelist = False
    guibyprop = getPropertyMap(mlist)
    try:
        globals = {'mlist': mlist}
        # Any exception that occurs in execfile() will cause the list to not
        # be saved, but any other problems are not save-fatal.
        execfile(infile, globals)
        savelist = True
        for k, v in globals.items():
            if k in ('mlist', '__builtins__'):
                continue
            if not hasattr(mlist, k):
                print >> sys.stderr, _('attribute "$k" ignored')
                continue
            if verbose:
                print >> sys.stderr, _('attribute "$k" changed')
            missing = []
            gui, wtype = guibyprop.get(k, (missing, missing))
            if gui is missing:
                # This isn't an official property of the list, but that's
                # okay, we'll just restore it the old fashioned way
                print >> sys.stderr, _('Non-standard property restored: $k')
                setattr(mlist, k, v)
            else:
                # BAW: This uses non-public methods.  This logic taken from
                # the guts of GUIBase.handleForm().
                try:
                    validval = gui._getValidValue(mlist, k, wtype, v)
                except ValueError:
                    print >> sys.stderr, _('Invalid value for property: $k')
                except errors.EmailAddressError:
                    print >> sys.stderr, _(
                        'Bad email address for option $k: $v')
                else:
                    # BAW: Horrible hack, but then this is special cased
                    # everywhere anyway. :(  Privacy._setValue() knows that
                    # when ALLOW_OPEN_SUBSCRIBE is false, the web values are
                    # 0, 1, 2 but these really should be 1, 2, 3, so it adds
                    # one.  But we really do provide [0..3] so we need to undo
                    # the hack that _setValue adds. :( :(
                    if k == 'subscribe_policy' and \
                           not config.ALLOW_OPEN_SUBSCRIBE:
                        validval -= 1
                    # BAW: Another horrible hack.  This one is just too hard
                    # to fix in a principled way in Mailman 2.1
                    elif k == 'new_member_options':
                        # Because this is a Checkbox, _getValidValue()
                        # transforms the value into a list of one item.
                        validval = validval[0]
                        validval = [bitfield for bitfield, bitval
                                    in config.OPTINFO.items()
                                    if validval & bitval]
                    gui._setValue(mlist, k, validval, fakedoc)
            # BAW: when to do gui._postValidate()???
    finally:
        if savelist and not checkonly:
            mlist.Save()
        mlist.Unlock()



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)
    listname = args[0]

    # Sanity check
    if opts.inputfile and opts.outputfile:
        parser.error(_('Only one of -i or -o is allowed'))
    if not opts.inputfile and not opts.outputfile:
        parser.error(_('One of -i or -o is required'))

    if opts.outputfile:
        do_output(listname, opts.outputfile, parser)
    else:
        do_input(listname, opts.inputfile, opts.checkonly,
                 opts.verbose, parser)



if __name__ == '__main__':
    main()
