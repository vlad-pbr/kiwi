#!/usr/bin/env python2
#kiwidesc=greet anybody!
import argparse
import sys

def kiwi_main():
	parser = argparse.ArgumentParser(description='Greet anybody!')
        parser.add_argument('-n', '--name', type=str)
	args = parser.parse_args()
	
	print "Hello, {}!".format(args.name if args.name else 'world')
