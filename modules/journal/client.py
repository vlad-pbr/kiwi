#!/usr/bin/env python3

"""
Usage examples:

	* kiwi journal -t diary -l
	* kiwi journal -t writing -f /path/to/a/new/story/I/wrote.txt

You can use this module to keep tabs on basically anything: log day to day stuff or keep memos of things.
I personally needed this module when learning how to drive and getting my license.
It really helped me keep tabs on my progress and see how many lessons I've done and money I spent.
"""

import argparse
from os.path import isfile, join, getsize
from datetime import datetime
from subprocess import call
from tempfile import mkstemp
from os import remove, close

def get_timestamp():
	return datetime.now().strftime("%B %d, %Y at %H:%M")

def read(kiwi, topic, from_file=None):
	if not from_file:
		_, content = kiwi.module('storage', 'source -r -S {} -n {}'.format(join(kiwi.module_home, 'sources'), topic), foreground=False)
		return content
	
	_, content = kiwi.module('storage', 'retrieve -s file -d {}'.format(from_file), foreground=False)
	return content

def get_topics(kiwi):
	_, topics = kiwi.module('storage', "source -l -S {}".format(join(kiwi.module_home, 'sources')), foreground=False)
	return topics

def write(kiwi, log, topic):

	# get existing logs and append new content
	journal = read(kiwi, topic)

	if len(journal.split('\n')) < 4:
		if kiwi.ask('Topic does not exist. Create?', ['y', 'n']) != 'y':
			return
		else:
			log = format_log(log)

	else:
		log = journal + format_log(log)

	# use storage module to store the journal
	kiwi.module('storage', 'source -S {} -m "{}" -n {} -c "{}"'.format(join(kiwi.module_home, 'sources'), get_timestamp(), topic, log), foreground=True)

def format_log(log):
	out = '-'*50 + '\n'
	out += get_timestamp() + '\n'
	out += '-'*50 + '\n'
	out += log.rstrip('\n') + '\n'*3
	return out

def kiwi_main(kiwi):

	parser = argparse.ArgumentParser(description=kiwi.module_desc,
									 epilog=__doc__,
									 formatter_class=argparse.RawDescriptionHelpFormatter)

	# log content options
	content_group = parser.add_mutually_exclusive_group()
	content_group.add_argument('-l', '--log', help='directly write content to be stored in a journal', action='store_true')
	content_group.add_argument('-f', '--file', help='path to the content to be stored in a journal', type=str)

	# journal actions
	action_group = parser.add_mutually_exclusive_group(required=True)
	action_group.add_argument('-t', '--topic', help='name of the topic', type=str)
	action_group.add_argument('-L', '--list-topics', help='show existing topics', action='store_true')
	
	args = parser.parse_args()

	# journal needs its sources
	if not isfile('sources'):
		print('You need to set up your journal sources using the kiwi storage module.')

	# list journals
	elif args.list_topics:
		print(get_topics(kiwi))

	# print journal
	elif not args.log and not args.file:
		print(read(kiwi, args.topic)),

	# write to journal
	else:

		# read from file
		if args.file:
			if isfile(args.file):
				log = read(kiwi, args.topic, args.file)
			else:
				print('Given file does not exist. Make sure the path to file is absolute.')
				return

		# get log from editor
		else:

			# create new temp file and prompt
			log_file_fd, log_file_path = mkstemp()
			close(log_file_fd)
			call('vi {}'.format(log_file_path), shell=True)

			# ensure content was written
			if getsize(log_file_path) == 0:
				print("No content was stored.")
				return

			# read from temp file and delete
			with open(log_file_path, 'r') as log_file:
				log = log_file.read()
			remove(log_file_path)

		write(kiwi, log, args.topic)
