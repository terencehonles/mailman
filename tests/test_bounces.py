# Copyright (C) 2001 by the Free Software Foundation, Inc.
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

"""Test the bounce detection modules."""

import sys
import os
import unittest

from mimelib.Parser import Parser



class BounceTest(unittest.TestCase):
    DATA = (
        # Postfix bounces
        ('Postfix', 'postfix_01.txt', ['xxxxx@local.ie']),
        ('Postfix', 'postfix_02.txt', ['yyyyy@digicool.com']),
        ('Postfix', 'postfix_03.txt', ['ttttt@ggggg.com']),
        ('Postfix', 'postfix_04.txt', ['davidlowie@mail1.keftamail.com']),
        ('Postfix', 'postfix_05.txt', ['bjelf@detectit.net']),
        # SimpleMatch bounces
        ('SimpleMatch', 'sendmail_01.txt', ['zzzzz@nfg.nl']),
        ('SimpleMatch', 'simple_01.txt', ['bbbsss@turbosport.com']),
        ('SimpleMatch', 'simple_02.txt', ['chris.ggggmmmm@usa.net']),
        ('SimpleMatch', 'newmailru_01.txt', ['zzzzz@newmail.ru']),
        # SimpleWarning
        ('SimpleWarning', 'simple_03.txt', ['jacobus@geo.co.za']),
        # GroupWise
        ('GroupWise', 'groupwise_01.txt', ['thoff@MAINEX1.ASU.EDU']),
        # Yale's own
        ('Yale', 'yale_01.txt', ['thomas.dtankengine@cs.yale.edu',
                                 'thomas.dtankengine@yale.edu']),
        # DSN, i.e. RFC 1894
        ('DSN', 'dsn_01.txt', ['JimmyMcEgypt@go.com']),
        ('DSN', 'dsn_02.txt', ['zzzzz@zeus.hud.ac.uk']),
        ('DSN', 'dsn_03.txt', ['ddd.kkk@advalvas.be']),
        ('DSN', 'dsn_04.txt', ['max.haas@unibas.ch']),
        ('DSN', 'dsn_05.txt', ['pkocmid@atlas.cz']),
        # Can't be tested:
        # dumbass_01.txt - We love Microsoft. :(
        # Done
        )

    def checkBounce(self):
        for modname, file, addrs in self.DATA:
            module = 'Mailman.Bouncers.' + modname
            __import__(module)
            fp = open(os.path.join('tests', 'bounces', file))
            try:
                msg = Parser().parse(fp)
            finally:
                fp.close()
            foundaddrs = sys.modules[module].process(msg)
            addrs.sort()
            foundaddrs.sort()
            try:
                assert addrs == foundaddrs
            except AssertionError:
                print >> sys.stderr, 'File: %s\nWanted: %s\nGot: %s' % (
                    fp.name, addrs, foundaddrs)
                raise



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BounceTest, 'check'))
    return suite



if __name__ == '__main__':
    unittest.main(defaultTest='suite')

