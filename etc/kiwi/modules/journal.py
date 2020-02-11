#!/usr/bin/env python2
kiwi_dependencies = ['storage']

import argparse
from datetime import datetime
from subprocess import Popen, PIPE
import shlex

journal_home_dir = None

def get_timestamp():
	return datetime.now().strftime("%B %d, %Y at %H:%M")

def command(cmd):
	return Popen(shlex.split(cmd), stdout=PIPE).communicate()[0]

def read(topic):
	return command('kiwi storage source -r -S {} -n {}'.format(\
                journal_home_dir + 'sources', topic))

def get_topics():
	return command('kiwi storage source -l -S {}'.format(\
                journal_home_dir + 'sources'))

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
	stdout = command('kiwi storage source -S {} -m "{}" -n {} -c "{}"'.format(\
                journal_home_dir + 'sources', get_timestamp(), topic, log))
	print stdout.rstrip(),

def format_log(log):
	out = '-'*50 + '\n'
	out += get_timestamp() + '\n'
	out += '-'*50 + '\n'
	out += log.rstrip('\n') + '\n'*3
	return out

def kiwi_main(kiwi):

	"""Log your thoughts and progress on different topics"""

	global journal_home_dir
	journal_home_dir = kiwi['module_home']

	parser = argparse.ArgumentParser(description=kiwi_main.__doc__)

	# log content options
	content_group = parser.add_mutually_exclusive_group()
	content_group.add_argument('-l', '--log', help='string content to be stored in a journal', type=str)
	content_group.add_argument('-f', '--file', help='path to the content to be stored in a journal', type=str)

	# journal actions
	action_group = parser.add_mutually_exclusive_group(required=True)
	action_group.add_argument('-t', '--topic', help='name of the topic', type=str)
	action_group.add_argument('-L', '--list-topics', help='show existing topics', action='store_true')
	
	args = parser.parse_args()

	# list journals
	if args.list_topics:
		print get_topics(),

	# print journal
	elif not args.log and not args.file:
		print read(args.topic),

	# write to journal
	else:
		log = args.log

		if args.file:
			log = read(args.file)

		write(log, args.topic)
