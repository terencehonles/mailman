#! /usr/bin/python

# A simple script to check the status of the translation.

import sys, string
from pprint import pprint

def chop (line):
    if line[-2:] == '\r\n':
        line = line[:-2]

    if line[-1:] == '\n':
        line = line[:-1]

    return line

name = None
revision = None

files = {}

for line in sys.stdin.readlines ():
    parts = string.split (chop (line))

    if len (parts) > 0:
        if parts[0] == 'File:':
            name = parts[1]
        elif parts[0] == 'Repository':
            files[name] = parts[2]

# pprint (files)

for line in open ('status', 'r').readlines ():
    parts = string.split (chop (line))

    if len (parts) > 0:
        if files.has_key (parts[0]):
            pass    # check the version

            if files[parts[0]] != parts[1]:
                print 'Update: %s (%s -> %s)' % (parts[0], parts[1], files[parts[0]])

            del files[parts[0]] # delete the item
        else:
            print 'Delete:', parts[0]

for file in files.keys ():
    print 'New:', file
