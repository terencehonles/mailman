# This is mailman's interface to the alias database.

# TODO:

# Write a wrapper program w/ root uid that allows the mailman user
# only to update the alias database.

import string
_file = open('/etc/aliases', 'r')
_lines = _file.readlines()
aliases = {}
_cur_line  = None

def _AddAlias(line):
  line = string.strip(line)
  if not line:
    return
  colon_index = string.find(line, ":")
  if colon_index < 1:
    raise "SyntaxError", "Malformed /etc/aliases file"
  alias = string.lower(string.strip(line[:colon_index]))
  rest = string.split(line[colon_index+1:], ",")
  rest = map(string.strip, rest)
  aliases[alias] = rest

for _line in _lines:
  if _line[0] == '#':
    continue
  if _line[0] == ' ' or _line[0] == '\t':
    _cur_line = _cur_line + _line
    continue
  if _cur_line:
    _AddAlias(_cur_line)
  _cur_line = _line
  
def GetAlias(str):
  str = string.lower(str)
  if not aliases.has_key(str):
    raise KeyError, "No such alias"
  return aliases[str]
	  
