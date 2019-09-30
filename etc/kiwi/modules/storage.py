#!/usr/bin/env python2
#kiwidesc=work with common file storage services to store and retrieve files
import argparse
import requests
import base64
import json

service_args = {
	'file': [],
	'github': ['repo', 'repo_owner', 'auth_user', 'auth_pass']
}

def file_store(args):
	with open(args.destination, 'w') as destination_file:
		destination_file.write(args.content)

def file_retrieve(args):
	with open(args.destination, 'r') as destination_file:
		return destination_file.read()

def github_store(args):
	# get remote file
	response = requests.get('https://{}:{}@api.github.com/repos/{}/{}/contents/{}'.format( \
                args.auth_user, args.auth_pass, args.repo_owner, args.repo, args.destination)).json()

	# write headers and data
	headers = {'Content-type': 'application/json'}
	commit_json = {
		'message': args.message if args.message else 'No message',
		'content': base64.b64encode(bytes(args.content), 'utf-8'),
		'committer': {}
	}

	# insert optional parameters
	if args.committer_user:
		commit_json['committer']['name'] = args.committer_user
	if args.committer_email:
                commit_json['committer']['email'] = args.committer_email
	if len(commit_json['committer']) is 0:
		del commit_json['committer']

	# file blob sha must be present if updating
	if 'sha' in response:
		commit_json['sha'] = response['sha']

	# update/create a file
	requests.put('https://{}:{}@api.github.com/repos/{}/{}/contents/{}'.format( \
		args.auth_user, args.auth_pass, args.repo_owner, args.repo, args.destination), data=json.dumps(commit_json), headers=headers).json()

def github_retrieve(args):
	return requests.get('https://{}:{}@raw.githubusercontent.com/{}/{}/master/{}'.format( \
		args.auth_user, args.auth_pass, args.repo_owner, args.repo, args.destination)).text

def kiwi_main():
	parser = argparse.ArgumentParser(description="work with common file storage services to store and retrieve files")
	subparsers = parser.add_subparsers(title='actions', dest='action')
	subparsers.required=True

	store_parser = subparsers.add_parser('store', help='store file within the storage service')
	retrieve_parser = subparsers.add_parser('retrieve', help='retrieve file from the storage service', conflict_handler="resolve")
	
	# file contents
	content_group = store_parser.add_mutually_exclusive_group(required=True)
	content_group.add_argument('-c', '--content', help='file content', type=str)
	content_group.add_argument('-f', '--file', help='source file to be stored', type=str)

	retrieve_parser.add_argument('-f', '--file', help='local file destination', type=str)
	retrieve_parser.add_argument('-h', '--hide', help='do not print out the retrieved data', action='store_true')

	for name, subparser in subparsers.choices.items():

		# required arguments
		subparser.add_argument('-s', '--service', help='storage service', type=str, required=True)
		subparser.add_argument('-d', '--destination', help='file path within the storage', type=str, required=True)

		# optional arguments
		subparser.add_argument('-r', '--repo', help='repository name (when using Git)', type=str)
		subparser.add_argument('-o', '--repo-owner', help='repository owner (when using Git)', type=str)
		subparser.add_argument('-m', '--message', help='commit message (when using Git)', type=str)
		subparser.add_argument('-u', '--auth-user', help='authentication username', type=str)
		subparser.add_argument('-p', '--auth-pass', help='authentication password', type=str)
		subparser.add_argument('-n', '--committer-user', help='name of the committer (when using Git)', type=str)
		subparser.add_argument('-e', '--committer-email', help='e-mail of the committer (when using Git)', type=str)

	args = parser.parse_args()

	# make sure service is supported and has all the required parameters
	if args.service in list(service_args):
		for attribute, value in args.__dict__.iteritems():
			if attribute in service_args[args.service] and not value:
				print "{}: missing '{}' argument".format(args.service, attribute)
				exit()

		if args.action == 'store':
			# store file contents in a variable
			if args.file:
				with open(args.file, 'r') as content_file:
					args.content = content_file.read()

			globals()[args.service + '_store'](args)

		else:
			data = globals()[args.service + '_retrieve'](args)

			if not args.hide:
				print data

			# store data in a file
			if args.file:
				with open(args.file, 'w') as content_file:
					content_file.write(data)
	else:
		print "Service '{}' is not supported".format(args.service)	
