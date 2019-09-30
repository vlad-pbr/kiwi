#!/usr/bin/env python2
#kiwidesc=work with common file storage services to store and retrieve files
import argparse

service_args = {
	'file': [],
	'github': ['repo', 'repo_owner', 'auth_user', 'auth_pass']
}

def file(args):
	with open(args.destination, 'w') as destination_file:
		destination_file.write(args.content)

# TODO
def github(args):
	pass

def kiwi_main():
	parser = argparse.ArgumentParser(description="work with common file storage services to store and retrieve files")

	# file contents
	content_group = parser.add_mutually_exclusive_group(required=True)
	content_group.add_argument('-c', '--content', type=str)
	content_group.add_argument('-f', '--file', type=str)

	# required arguments
	parser.add_argument('-s', '--service', help='storage service', type=str, required=True)
	parser.add_argument('-d', '--destination', help='file path within the storage', type=str, required=True)

	# optional arguments
	parser.add_argument('-r', '--repo', help='repository name (when using Git)', type=str)
	parser.add_argument('-o', '--repo-owner', help='repository owner (when using Git)', type=str)
	parser.add_argument('-m', '--message', help='commit message (when using Git)', type=str)
	parser.add_argument('-u', '--auth_user', help='authentication username', type=str)
	parser.add_argument('-p', '--auth_pass', help='authentication password', type=str)

	args = parser.parse_args()

	# make sure service is supported and has all the required parameters
	if args.service in list(service_args):
		for attribute, value in args.__dict__.iteritems():
			if attribute in service_args[args.service] and not value:
				print 'Missing {}'.format(attribute)
				exit()

		# store file contents in a variable
		if args.file:
			with open(args.file, 'r') as content_file:
				args.content = content_file.read()

		globals()[args.service](args)
	else:
		print "Service '{}' is not supported".format(args.service)	
