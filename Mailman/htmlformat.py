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


"""Library for program-based construction of an HTML documents.

Encapsulate HTML formatting directives in classes that act as containers
for python and, recursively, for nested HTML formatting objects.
"""


# Eventually could abstract down to HtmlItem, which outputs an arbitrary html
# object given start / end tags, valid options, and a value.  Ug, objects
# shouldn't be adding their own newlines.  The next object should.


import types
import string
import mm_cfg
import Utils
from Mailman.i18n import _


# Format an arbitrary object.
def HTMLFormatObject(item, indent):
    "Return a presentation of an object, invoking their Format method if any."
    if type(item) == type(''):
	return item
    elif not hasattr(item, "Format"):
	return `item`
    else:
	return item.Format(indent)

def CaseInsensitiveKeyedDict(d):
    result = {}
    for (k,v) in d.items():
	result[string.lower(k)] = v
    return result

# Given references to two dictionaries, copy the second dictionary into the
# first one.
def DictMerge(destination, fresh_dict):
    for (key, value) in fresh_dict.items():
	destination[key] = value

class Table:
    def __init__(self, **table_opts):
	self.cells = []
	self.cell_info = {}
	self.row_info = {}
	self.opts = table_opts

    def AddOptions(self, opts):
	DictMerge(self.opts, opts)

    # Sets all of the cells.  It writes over whatever cells you had there
    # previously.

    def SetAllCells(self, cells):
	self.cells = cells

    # Add a new blank row at the end
    def NewRow(self):
	self.cells.append([])

    # Add a new blank cell at the end
    def NewCell(self):
	self.cells[-1].append('')
	
    def AddRow(self, row):
	self.cells.append(row)

    def AddCell(self, cell):
	self.cells[-1].append(cell)

    def AddCellInfo(self, row, col, **kws):
	kws = CaseInsensitiveKeyedDict(kws)
	if not self.cell_info.has_key(row):
	    self.cell_info[row] = { col : kws }
	elif self.cell_info[row].has_key(col):
	    DictMerge(self.cell_info[row], kws)
	else:
	    self.cell_info[row][col] = kws
	
    def AddRowInfo(self, row, **kws):
	kws = CaseInsensitiveKeyedDict(kws)
	if not self.row_info.has_key(row):
	    self.row_info[row] = kws
	else:
	    DictMerge(self.row_info[row], kws)

    # What's the index for the row we just put in?
    def GetCurrentRowIndex(self):
	return len(self.cells)-1
    
    # What's the index for the col we just put in?
    def GetCurrentCellIndex(self):
	return len(self.cells[-1])-1

    def ExtractCellInfo(self, info):
	valid_mods = ['align', 'valign', 'nowrap', 'rowspan', 'colspan',
		      'bgcolor']
	output = ''

	for (key, val) in info.items():
	    if not key in valid_mods:
		continue
	    if key == 'nowrap':
		output = output + ' NOWRAP'
		continue
	    else:
		output = output + ' %s="%s"' %(string.upper(key), val) 

	return output

    def ExtractRowInfo(self, info):
	valid_mods = ['align', 'valign', 'bgcolor']
	output = ''

	for (key, val) in info.items():
	    if not key in valid_mods:
		continue
	    output = output + ' %s="%s"' %(string.upper(key), val) 

	return output

    def ExtractTableInfo(self, info):
	valid_mods = ['align', 'width', 'border', 'cellspacing', 'cellpadding',
		      'bgcolor']

	output = ''

	for (key, val) in info.items():
	    if not key in valid_mods:
		continue
	    if key == 'border' and val == None:
		output = output + ' BORDER'
		continue
	    else:	
		output = output + ' %s="%s"' %(string.upper(key), val) 	

	return output

    def FormatCell(self, row, col, indent):
	try:
	    my_info = self.cell_info[row][col]
	except:
	    my_info = None

	output = '\n' + ' '*indent + '<td'
	if my_info:
	    output = output + self.ExtractCellInfo(my_info)
	item = self.cells[row][col]
	item_format = HTMLFormatObject(item, indent+4)
	output = '%s>%s</td>' % (output, item_format)
	return output

    def FormatRow(self, row, indent):
	try:
	    my_info = self.row_info[row]
	except:
	    my_info = None

	output = '\n' + ' '*indent + '<tr'
	if my_info:
	    output = output + self.ExtractRowInfo(my_info)
	output = output + '>'

        for i in range(len(self.cells[row])):
            output = output + self.FormatCell(row, i, indent + 2)

	output = output + '\n' + ' '*indent + '</tr>'

	return output

    def Format(self, indent=0):
	output = '\n' + ' '*indent + '<table'
	output = output + self.ExtractTableInfo(self.opts)
	output = output + '>'

	for i in range(len(self.cells)):
	    output = output + self.FormatRow(i, indent + 2)

	output = output + '\n' + ' '*indent + '</table>\n'

	return output
	

class Link:
    def __init__(self, href, text, target=None):
	self.href = href
	self.text = text
	self.target = target
    
    def Format(self, indent=0):
        texpr = ""
        if self.target != None:
	    texpr = ' target="%s"' % self.target
	return '<a href="%s"%s>%s</a>' % (HTMLFormatObject(self.href, indent),
					  texpr,
					  HTMLFormatObject(self.text, indent))

class FontSize:
    """FontSize is being deprecated - use FontAttr(..., size="...") instead."""
    def __init__(self, size, *items):
	self.items = list(items)
	self.size = size
    
    def Format(self, indent=0):
	output = '<font size="%s">' % self.size
	for item in self.items:
	    output = output + HTMLFormatObject(item, indent)
	output = output + '</font>'
	return output

class FontAttr:
    """Present arbitrary font attributes."""
    def __init__(self, *items, **kw):
	self.items = list(items)
	self.attrs = kw
    
    def Format(self, indent=0):
	seq = []
	for k, v in self.attrs.items():
	    seq.append('%s="%s"' % (k, v))
	output = '<font %s>' % string.join(seq, ' ')
	for item in self.items:
	    output = output + HTMLFormatObject(item, indent)
	output = output + '</font>'
	return output


class Container:
    def __init__(self, *items):
	if not items:
	    self.items = []
	else:
	    self.items = items

    def AddItem(self, obj):
	self.items.append(obj)

    def Format(self, indent=0):
        output = []
        for item in self.items:
            output.append(HTMLFormatObject(item, indent))
        return string.join(output, '')


class Label(Container):
    align = 'right'

    def __init__(self, *items):
        Container.__init__(self, *items)

    def Format(self, indent=0):
        return ('<div align="%s">' % self.align) + \
               Container.Format(self, indent) + \
               '</div>'


# My own standard document template.  YMMV.
# something more abstract would be more work to use...

class Document(Container):
    title = None
    language = None

    def set_language(self, lang=None):
        self.language = lang

    def get_content_type(self):
        ctype = 'Content-type: text/html'
        if self.language:
            ctype += '; charset=' + Utils.GetCharSet(self.language)
        return ctype

    def SetTitle(self, title):
	self.title = title

    def Format(self, indent=0, **kws):
        tab = ' ' * indent

        output = [self.get_content_type(),
                  '',
                  tab,
                  '<HTML>',
                  '<HEAD>'
                  ]
        if self.title:
            output.append('%s<TITLE>%s</TITLE>' % (tab, self.title))
        output.append('%s</HEAD>' % tab)
        output.append('%s<BODY' % tab)
	quals = []
	for k, v in kws.items():
	    quals.append('%s="%s"' % (k, v))
        output.append('%s<BODY %s>' % (tab, string.join(quals, ' ')))
        output.append(Container.Format(self, indent))
        output.append('%s</BODY>' % tab)
        output.append('%s</HTML>' % tab)
        return string.join(output, '\n')


class HeadlessDocument(Document):
    """Document without head section, for templates that provide their own."""
    def Format(self, indent=0, **kws):
        return self.get_content_type() + '\n\n' + \
               Container.Format(self, indent)
    
class StdContainer(Container):
    def Format(self, indent=0):
	# If I don't start a new I ignore indent
	output = '<%s>' % self.tag
	output = output + Container.Format(self, indent)
	output = '%s</%s>' % (output, self.tag)
	return output	    


class QuotedContainer(Container):
    def Format(self, indent=0):
	# If I don't start a new I ignore indent
	output = '<%s>%s</%s>' % (
            self.tag,
            Utils.QuoteHyperChars(Container.Format(self, indent)),
            self.tag)
	return output

class Header(StdContainer):
    def __init__(self, num, *items):
	self.items = items
	self.tag = 'h%d' % num

class Address(StdContainer):
    tag = 'address'

class Underline(StdContainer):
    tag = 'u'
	
class Bold(StdContainer):
    tag = 'strong'  

class Italic(StdContainer):
    tag = 'em'

class Preformatted(QuotedContainer):
    tag = 'pre'

class Subscript(StdContainer):
    tag = 'sub'

class Superscript(StdContainer):
    tag = 'sup'

class Strikeout(StdContainer):
    tag = 'strike'

class Center(StdContainer):
    tag = 'center'

class Form(Container):
    def __init__(self, action='', method='POST', encoding=None, *items):
	apply(Container.__init__, (self,) +  items)
	self.action = action
	self.method = method
        self.encoding = encoding

    def set_action(self, action):
        self.action = action

    def Format(self, indent=0):
	spaces = ' ' * indent
        encoding = ''
        if self.encoding:
            encoding = 'enctype="%s"' % self.encoding
	output = '\n%s<FORM action="%s" method="%s" %s>\n' % (
            spaces, self.action, self.method, encoding)
	output = output + Container.Format(self, indent+2)
	output = '%s\n%s</FORM>\n' % (output, spaces)
	return output


class InputObj:
    def __init__(self, name, ty, value, checked, **kws):
	self.name = name
	self.type = ty
	self.value = value
	self.checked = checked
	self.kws = kws

    def Format(self, indent=0):
	output = ['<INPUT name="%s" type="%s" value="%s"' %
                  (self.name, self.type, self.value)]
        for item in self.kws.items():
            output.append('%s="%s"' % item)
        if self.checked:
            output.append('CHECKED')
        output.append('>')
        return string.join(output, ' ')


class SubmitButton(InputObj):
    def __init__(self, name, button_text):
	InputObj.__init__(self, name, "SUBMIT", button_text, checked=0)

class PasswordBox(InputObj):
    def __init__(self, name, value='', size=mm_cfg.TEXTFIELDWIDTH):
	InputObj.__init__(self, name, "PASSWORD", value, checked=0, size=size)

class TextBox(InputObj):
    def __init__(self, name, value='', size=mm_cfg.TEXTFIELDWIDTH):
	InputObj.__init__(self, name, "TEXT", value, checked=0, size=size)

class Hidden(InputObj):
    def __init__(self, name, value=''):
        InputObj.__init__(self, name, 'HIDDEN', value, checked=0)

class TextArea:
    def __init__(self, name, text='', rows=None, cols=None, wrap='soft'):
	self.name = name
	self.text = text
	self.rows = rows
	self.cols = cols
	self.wrap = wrap

    def Format(self, indent=0):
	output = '<TEXTAREA NAME=%s' % self.name
	if self.rows:
	    output = output + ' ROWS=%s' % self.rows
	if self.cols:
	    output = output + ' COLS=%s' % self.cols
	if self.wrap:
	    output = output + ' WRAP=%s' % self.wrap
	output = output + '>%s</TEXTAREA>' % self.text
	return output

class FileUpload(InputObj):
    def __init__(self, name, rows=None, cols=None, **kws):
        apply(InputObj.__init__, (self, name, 'FILE', '', 0), kws)

class RadioButton(InputObj):
    def __init__(self, name, value, checked=0, **kws):
	apply(InputObj.__init__, (self, name, 'RADIO', value, checked), kws)

class CheckBox(InputObj):
    def __init__(self, name, value, checked=0, **kws):
        apply(InputObj.__init__, (self, name, "CHECKBOX", value, checked), kws)



class VerticalSpacer:
    def __init__(self, size=10):
	self.size = size
    def Format(self, indent=0):
	output = '<spacer type="vertical" height="%d">' % self.size
	return output 

class RadioButtonArray:
    def __init__(self, name, button_names, checked=None, horizontal=1,
                 values=None):
	self.button_names = button_names
	self.horizontal = horizontal
	self.name = name
	self.checked = checked
	self.horizontal = horizontal
        if values is not None:
            assert len(values) == len(button_names)
            self.values = values
        else:
            self.values = range(len(button_names))

    def Format(self, indent=0):
	t = Table(cellspacing=5)
        items = []
        for i, name, value in map(None,
                                  range(len(self.button_names)),
                                  self.button_names,
                                  self.values):
            ischecked = (self.checked == i)
            item = RadioButton(self.name, value, ischecked).Format() + name
            items.append(item)
            if not self.horizontal:
                t.AddRow(items)
                items = []
	if self.horizontal:
	    t.AddRow(items)
	return t.Format(indent)

class UnorderedList(Container):
    def Format(self, indent=0):
	spaces = ' ' * indent
	output = '\n%s<ul>\n' % spaces
	for item in self.items:
	    output = output + '%s<li>%s\n' % \
                     (spaces, HTMLFormatObject(item, indent + 2))
	output = output + '%s</ul>\n' % spaces
	return output

class OrderedList(Container):
    def Format(self, indent=0):
	spaces = ' ' * indent
	output = '\n%s<ol>\n' % spaces
	for item in self.items:
	    output = output + '%s<li>%s\n' % \
                     (spaces, HTMLFormatObject(item, indent + 2))
	output = output + '%s</ol>\n' % spaces
	return output
	
class DefinitionList(Container):
    def Format(self, indent=0):
        spaces = ' ' * indent
        output = '\n%s<dl>\n' % spaces
        for dt, dd in self.items:
            output = output + '%s<dt>%s\n<dd>%s\n' % \
                     (spaces, HTMLFormatObject(dt, indent+2),
                      HTMLFormatObject(dd, indent+2))
        output = output + '%s</dl>\n' % spaces
        return output



# Logo constants
#
# These are the URLs which the image logos link to.  The Mailman home page now
# points at the gnu.org site instead of the www.list.org mirror.
#
from mm_cfg import MAILMAN_URL
PYTHON_URL  = 'http://www.python.org/'
GNU_URL     = 'http://www.gnu.org/'

# The names of the image logo files.  These are concatentated onto
# mm_cfg.IMAGE_LOGOS (not urljoined).
DELIVERED_BY = 'mailman.jpg'
PYTHON_POWERED = 'PythonPowered.png'
GNU_HEAD = 'gnu-head-tiny.jpg'


def MailmanLogo():
    t = Table(border=0, width='100%')
    if mm_cfg.IMAGE_LOGOS:
        def logo(file):
            return mm_cfg.IMAGE_LOGOS + file
        mmlink = '<img src="%s" alt="Delivered by Mailman" border=0>' \
                 '<br>version %s' % (logo(DELIVERED_BY), mm_cfg.VERSION)
        pylink = '<img src="%s" alt="Python Powered" border=0>' % \
                 logo(PYTHON_POWERED)
        gnulink = '<img src="%s" alt="GNU\'s Not Unix" border=0>' % \
                  logo(GNU_HEAD)
        t.AddRow([mmlink, pylink, gnulink])
    else:
        # use only textual links
        version = mm_cfg.VERSION
        mmlink = Link(MAILMAN_URL,
                      _('Delivered by Mailman<br>version %(version)s'))
        pylink = Link(PYTHON_URL, _('Python Powered'))
        gnulink = Link(GNU_URL, _("Gnu's Not Unix"))
        t.AddRow([mmlink, pylink, gnulink])
    return t


class SelectOptions:
   def __init__(self, varname, values, legend, 
                selected=0, size=1, multiple=None):
      self.varname  = varname
      self.values   = values
      self.legend   = legend
      self.size     = size
      self.multiple = multiple
      # we convert any type to tuple, commas are needed 
      if not multiple:
         if type(selected) == types.IntType:
             self.selected = (selected,)
         elif type(selected) == types.TupleType:
             self.selected = (selected[0],)
         elif type(selected) == types.ListType:
             self.selected = (selected[0],)
         else:
             self.selected = (0,)
 
   def Format(self, indent=0):
      spaces = " " * indent
      items  = min( len(self.values), len(self.legend) )

      # jcrey: If there is no argument, we return nothing to avoid errors
      if items == 0:
          return ""
 
      text = "\n" + spaces + "<Select name=\"%s\"" % self.varname
      if self.size > 1:
          text = text + " size=%d" % self.size
      if self.multiple:
          text = text + " multiple"
      text = text + ">\n"
 
      for i in range(items):
          if i in self.selected:
              checked = " Selected"
          else:
              checked = ""
 
          opt = " <option value=\"%s\"%s> %s </option>" % (
              self.values[i], checked, self.legend[i])
          text = text + spaces + opt + "\n"
 
      return text + spaces + '</Select>'
