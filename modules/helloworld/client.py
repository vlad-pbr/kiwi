#!/usr/bin/env python2

# Hi!
#
# This is a general template for a kiwi module. Comments below will guide you around.
# Copy this code, edit it, plug it into the module directory (/etc/kiwi/modules/<module-name>/client.py by default) and you're done.
# I tried to keep it as minimal as possible. Have fun!
#
# ~ Vlad

'''
This module shows you all of the features kiwi provides to its modules.
Should you wish to write your own module, use this module's code as a template:
https://github.com/vlad-pbr/kiwi/blob/master/modules/helloworld/client.py
'''

# this optional variable is a list of kiwi modules that this module utilizes
# kiwi will read this list and fetch the missing modules before running this module
# a good example would be the 'journal' module which uses the 'storage' module
kiwi_dependencies = []

import argparse

# the basic requirement for a kiwi module is to have a kiwi_main() method
def kiwi_main():

	# docstrings are kiwi's module descriptions

	"""Greet anybody!"""

	# most kiwi modules use argparse, most also use docstring as description
	parser = argparse.ArgumentParser(description=kiwi_main.__doc__, epilog=__doc__)
	parser.add_argument('-n', '--name', help='who should be greeted?', type=str)
	args = parser.parse_args()

	# 'kiwi' namespace injected into the module contains useful functions and variables
	if args.name:
		if args.name == kiwi.module_name:
			print 'Hello to you too!'
		else:
			print 'Hello, {}!'.format(args.name)

	# bait the first time user to read the instructions	
	else:
		print 'Hello, world!'
		print 'Tip: use --help flag to see how you greet others!'