#!/usr/bin/env python2
import argparse
import os
import errno
from datetime import datetime

journal_home_dir = os.path.expanduser("~") + '/.kiwi/journal/'
journal_journals_dir = journal_home_dir + 'journals/'

def get_timestamp():
	return datetime.now().strftime("%B %d, %Y at %H:%M")

def read(path):
	try:
		with open(path, 'r') as _file:
			return _file.read()
	except Exception as e:
		print 'could not read from {}: {}'.format(path, e)
		exit()

# TODO commit journal update
def commit():
	pass

def write(log, topic):
	try:
                os.makedirs(journal_journals_dir)
        except OSError as e:
                if e.errno is not errno.EEXIST:
			print 'could not create directory {}: {}'.format(journal_journals_dir, e)
			exit()

	open_mode = 'a'
	if not os.path.isfile(journal_journals_dir + topic):
		print "topic '{}' does not exist. Create? (y/n)".format(topic),
		if raw_input() == 'y':
			open_mode = 'w'
		else:
			exit()

	try:
		with open(journal_journals_dir + topic, open_mode) as topic_file:
			topic_file.write(format_log(log))
			print 'successful write'
	except Exception as e:
		print 'could not write to {}: {}'.format(journal_journals_dir + topic, e)
		exit()

def format_log(log):
	out = '-'*50 + '\n'
	out = out + get_timestamp() + '\n'
	out = out + '-'*50 + '\n'
	out = out + log.rstrip('\n') + '\n'*3
	
	return out

def kiwi_main():
        parser = argparse.ArgumentParser(description='log your progress on different topics')
	parser.add_argument('-l', '--log', const='', nargs='?', type=str)
	parser.add_argument('-t', '--topic', type=str)
	parser.add_argument('-f', '--file', type=str)

        args = parser.parse_args()

	if args.topic and args.log == None:
		if not os.path.isfile(journal_journals_dir + args.topic):
			print "topic '{}' does not exist".format(args.topic)
		else:
			print read(journal_journals_dir + args.topic)

	elif args.log != None:
		if not args.topic:
			print 'missing topic'
		elif args.log == '' and args.file == None:
			print 'missing log'
		elif args.log != '' and args.file:
			print "can't have both a file and an ad-hoc log specified"
		else:
			log = args.log

			if args.file:
				log = read(args.file)

			write(log, args.topic)
