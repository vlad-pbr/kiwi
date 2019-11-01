#!/usr/bin/env python2
#kiwidesc=log your thoughts and progress on different topics

import argparse
import os
import errno
from datetime import datetime
from subprocess import Popen, PIPE
import shlex

journal_home_dir = os.path.expanduser("~") + '/.kiwi/journal/'
journal_journals_dir = journal_home_dir + 'journals/'

def get_timestamp():
	return datetime.now().strftime("%B %d, %Y at %H:%M")

def module_installed(target_module):
	cmd = 'kiwi --list-modules'
        stdout = Popen(shlex.split(cmd), stdout=PIPE).communicate()[0]

	for module in stdout.split('\n'):
                if module[4:11] == target_module:
                        if module[1] == 'x':
				return True
	return False

def read(topic):
	cmd = 'kiwi storage source -r -S {} -n {}'.format(\
		journal_home_dir + 'sources', topic)

	return Popen(shlex.split(cmd), stdout=PIPE).communicate()[0]

def write(log, topic):

	# get existing logs and append new content
	journal = read(topic)

	if len(journal.split('\n')) < 4:
		print 'Topic does not exist. Create? (y/n):',
		if raw_input() != 'y':
			exit()
		else:
			log = format_log(log)

	else:
		log = journal + format_log(log)

	# use storage module to store the journal
	cmd = 'kiwi storage source -S {} -m "{}" -n {} -c "{}"'.format(\
		journal_home_dir + 'sources', get_timestamp(), topic, log)

	stdout = Popen(shlex.split(cmd), stdout=PIPE).communicate()[0]
	print stdout.rstrip(),

def format_log(log):
	out = '-'*50 + '\n'
	out += get_timestamp() + '\n'
	out += '-'*50 + '\n'
	out += log.rstrip('\n') + '\n'*3
	return out

def kiwi_main():
        parser = argparse.ArgumentParser(description='log your progress on different topics')

	# log content options
	content_group = parser.add_mutually_exclusive_group()
	content_group.add_argument('-l', '--log', help='string content to be stored in a journal', type=str)
	content_group.add_argument('-f', '--file', help='path to the content to be stored in a journal', type=str)

	# journal actions
	action_group = parser.add_mutually_exclusive_group(required=True)
	action_group.add_argument('-t', '--topic', help='name of the topic', type=str)
	action_group.add_argument('-L', '--list-topics', help='show existing topics', action='store_true')

        args = parser.parse_args()

	# make sure the storage module is installed
	if not module_installed('storage'):
		print "Error: kiwi 'storage' module not installed"
                print "Tip: use 'sudo kiwi -g storage' to install the module"
		exit()

	# list journals
	if args.list_topics:
		pass # TODO from first source of source file

	# print journal
	elif not args.log and not args.file:
		print read(args.topic),

	# write to journal
	else:
		log = args.log

		if args.file:
			log = read(args.file)

		write(log, args.topic)
