"""Decode encoded-words as defined by RFC 2047"""

import base64

class DecodeError(ValueError):
    __super_init = ValueError.__init__
    def __init__(self, msg):
        self.__super_init("invalid encoded-word: %s" % msg)

class Decoder:
    """Decode mail header encoded-word format defined by RFC 2047"""
    
    offset = 0

    def decode(self, s):
        """Decode an encoded-word

        Returns the charset of the encoded-word, the decoded text, and
        the position of the first character following the
        encoded-word.

        The first position of the input string must by the first
        character of the encoded-word.
        """
        if not s.startswith('=?'):
            raise DecodeError("must start with '=?', not %s" % repr(s[:2]))
        charset = self._get_charset(s)
        encoding = self._get_encoding(s)
        _text = self._get_text(s)

        if encoding == 'q':
            text = self._decode_q(_text)
        else:
            text = self._decode_b(_text)
        
        return charset, text, self.offset

    # XXX technically the charset and encoding can't contain SPACE,
    # CTLs, or especials; do not currently check this

    def _get_charset(self, s):
        i = s.find('?', 2)
        if i == -1:
            raise DecodeError("can't find of charset")
        self.offset = i + 1
        return s[2:i]

    _valid_encodings = ('q', 'b')

    def _get_encoding(self, s):
        i = s.find('?', self.offset)
        if i == -1:
            raise DecodeError("can't find encoding")
        enc = s[self.offset:i].lower()
        self.offset = i + 1
        if enc not in Decoder._valid_encodings:
            raise DecodeError("'%s' is not a valid encoding" % enc)
        return enc

    def _get_text(self, s):
        i = s.find('?=', self.offset)
        if i == -1:
            raise DecodeError("can't find end of encoded text")
        text = s[self.offset:i]
        self.offset = i + 2
        return text

    SPACE = chr(0x20)

    def _decode_q(self, s):
        """Q encoding defined by RFC 2047"""
        chunks = []
        offset = 0
        end = len(s)
        import sys
        while offset < end:
            i = s.find('=', offset)
            j = s.find('_', offset)
            if j == i == -1:
                chunks.append(s[offset:])
                break
            if (j < i and j != -1) or i == -1:
                chunks.append(s[offset:j])
                chunks.append(Decoder.SPACE)
                offset = j + 1
            else:
                chunks.append(s[offset:i])
                hexdig = s[i+1:i+3]
                chunks.append(chr(int(hexdig, 16)))
                offset = i + 3
        return "".join(chunks)

    def _decode_b(self, s):
        """B encoding == base64 encoding defined by RFC 2045"""
        import sys
        return base64.decodestring(s)

def decode(s):
    """Decode a string containing encoded words"""
    _decode = Decoder().decode

    chunks = []
    offset = 0
    charset = None
    while 1:
        i = s.find('=?', offset)
        if i == -1:
            chunks.append(s[offset:])
            break
        chunks.append(s[offset:i])
        _charset, text, offset = _decode(s[i:])
        offset = offset + i
        if charset is None:
            charset = _charset
        elif charset != _charset:
            raise ValueError, "can not decode string with multiple charsets"
        chunks.append(text)
    return "".join(chunks), charset

def test():
    examples = [
        # valid
        '=?US-ASCII?Q?Keith_Moore?= <moore@cs.utk.edu>',
        '=?ISO-8859-1?Q?Keld_J=F8rn_Simonsen?= <keld@dkuug.dk>',
        '=?ISO-8859-1?Q?Andr=E9_?= Pirard <PIRARD@vm1.ulg.ac.be>',
        '=?ISO-8859-1?B?SWYgeW91IGNhbiByZWFkIHRoaXMgeW8=?=',
        '=?ISO-8859-2?B?dSB1bmRlcnN0YW5kIHRoZSBleGFtcGxlLg==?=',
        '=?US-ASCII?Q?.._cool!?=',
        '=?ISO-8859-1?Q?Olle_J=E4rnefors?= <ojarnef@admin.kth.se>',
        '(=?iso-8859-8?b?7eXs+SDv4SDp7Oj08A==?=)',
        # invalid
        'abc',
        '=?abc',
        '=?abc?abc',
        '=?ISO-8859-1?abc?text',
        ]
    for s in examples:
        try:
            text, charset = decode(s)
        except ValueError, msg:
            print "error:", msg
        else:
            print text, charset

if __name__ == "__main__":
    test()
    
