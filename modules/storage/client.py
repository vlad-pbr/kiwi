#!/usr/bin/env python2

import argparse
import requests
import base64
import json
import os

service_args = {
	'file': [],
	'github': ['repo', 'repo_owner', 'auth_user', 'auth_token']
}

# ---------------------------------------------------------------------------------------------------

def file_store(args):
	with open(args.destination, 'w') as destination_file:
		destination_file.write(args.content)

	return 'saved to ' + args.destination

def file_retrieve(args):
	with open(args.destination, 'r') as destination_file:
		return destination_file.read()

def file_list(args):
	return '\n'.join(os.listdir(args.destination))

def github_store(args):
	# get remote file
	response = requests.get('https://{}:{}@api.github.com/repos/{}/{}/contents/{}'.format( \
                args.auth_user, args.auth_token, args.repo_owner, args.repo, args.destination)).json()

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
	response = requests.put('https://{}:{}@api.github.com/repos/{}/{}/contents/{}'.format( \
		args.auth_user, args.auth_token, args.repo_owner, args.repo, args.destination), data=json.dumps(commit_json), headers=headers).json()

	# message is received if commit failed
	if 'message' in response:
		return response['message'].replace('\n', ' ')
	
	return 'successful commit to {}/{}'.format(args.repo_owner, args.repo)

def github_retrieve(args):
	return requests.get('https://{}:{}@raw.githubusercontent.com/{}/{}/master/{}'.format( \
		args.auth_user, args.auth_token, args.repo_owner, args.repo, args.destination)).text

def github_list(args):
	item_list = requests.get('https://{}:{}@api.github.com/repos/{}/{}/contents/{}'.format( \
                args.auth_user, args.auth_token, args.repo_owner, args.repo, args.destination)).json()

	return '\n'.join([item['name'] for item in item_list if item['type'] == 'file'])


# ---------------------------------------------------------------------------------------------------

def store(args):
	print('{}:'.format(args.service), end=' ')
	
	try:
		response = globals()[args.service + '_store'](args)
		print('successful' if response is True else response)
	except Exception as e:
		print(e)

def retrieve(args):
	return globals()[args.service + '_retrieve'](args)

def list_items(args):
	return globals()[args.service + '_list'](args)

def missing_args(args, service):
	if service in list(service_args):
		for attribute in service_args[service]:
			if not attribute in args.__dict__ or not args.__dict__[attribute]:
				return "{}: missing '{}' argument".format(service, attribute)
		return None

	return "Service '{}' is not supported".format(service)

def parse_source(filepath):
	args_list = []

	with open(filepath, 'r') as sources:
		line = sources.readline()
 
		# split each line by space to get keyvalue strings
		while line:
			if line[0] != '#':
				args = argparse.Namespace()
				kvs = line.split(' ')

				# split each element by '=' to separate key and value
				for kv in kvs:
					kv = kv.split('=')
					args.__setattr__(kv[0], kv[1].strip())

				args_list.append(args)
			line = sources.readline()

	return args_list

def kiwi_main(kiwi):

	parser = argparse.ArgumentParser(description=kiwi.module_desc)
	subparsers = parser.add_subparsers(title='actions', dest='action')
	subparsers.required=True

	# define subparsers
	store_parser = subparsers.add_parser('store', help='store file within the storage service')
	retrieve_parser = subparsers.add_parser('retrieve', help='retrieve file from the storage service', conflict_handler="resolve")
	source_parser = subparsers.add_parser('source', help='use source file to store data within multiple services')
	
	# retrieve subparser specific arguments
	retrieve_parser.add_argument('-f', '--file', help='local file destination', type=str)
	retrieve_parser.add_argument('-h', '--hide', help='do not print out the retrieved data', action='store_true')

	# source parser specific arguments
	source_parser.add_argument('-S', '--source-file', help='destination to a file of sources', type=str, required=True)
	source_parser.add_argument('-n', '--filename', help='filename within the destination folder', required=False)

	for name, subparser in list(subparsers.choices.items()):

		# store / source common arguments
		if name != 'retrieve':

			# required arguments
			content_group = subparser.add_mutually_exclusive_group(required=True)
			content_group.add_argument('-c', '--content', help='file content', type=str)
			content_group.add_argument('-f', '--file', help='file contents of which should be stored', type=str)

			if name == 'source':
				content_group.add_argument('-r', '--retrieve', help='retrieve content instead of storing', action='store_true')
				content_group.add_argument('-l', '--list', help='list all file names in a given directory', action='store_true')

			# optional arguments
			subparser.add_argument('-m', '--message', help='commit message (when using Git)', type=str)
			subparser.add_argument('--committer-user', help='name of the committer (when using Git)', type=str)
			subparser.add_argument('--committer-email', help='e-mail of the committer (when using Git)', type=str)

		# store / retrieve common arguments
		if name != 'source':

			# required arguments
			subparser.add_argument('-s', '--service', help='storage service', type=str, choices=list(service_args.keys()), required=True)
			subparser.add_argument('-d', '--destination', help='file path within the storage', type=str, required=True)

			# optional arguments
			subparser.add_argument('-r', '--repo', help='repository name (when using Git)', type=str)
			subparser.add_argument('-o', '--repo-owner', help='repository owner (when using Git)', type=str)
			subparser.add_argument('-u', '--auth-user', help='authentication username', type=str)
			subparser.add_argument('-p', '--auth-pass', help='authentication password', type=str)
			subparser.add_argument('-t', '--auth-token', help='authentication token', type=str)

	args = parser.parse_args()

	# source action
	if args.action == 'source':

		# parse source file, get list of namespaces
		args_list = parse_source(args.source_file)

		# for each source
		for arg in args_list:

			# check if any arguments are missing
			missing = missing_args(arg, arg.service)

			if not missing:

				# set optional arguments
				for attribute in store_parser._get_optional_actions():
					if not arg.__contains__(attribute.dest):
						if args.__contains__(attribute.dest):
							arg.__setattr__(attribute.dest, args.__dict__[attribute.dest])
						else:
							arg.__setattr__(attribute.dest, None)

				# set full destination
				if args.filename:
                                	arg.destination = os.path.join(arg.destination, args.filename)

				if args.retrieve:
					print(retrieve(arg), end=' ')
					return
				elif args.list:
					print(list_items(arg), end=' ')
					return
				else:

					# read from file if filepath is given
					if args.file:
                        	        	with open(args.file, 'r') as content_file:
                                        		arg.content = content_file.read()
					else:
						arg.content = args.content

					store(arg)
			else:
				print(missing)

	# adhoc action
	else:

		# check if any arguments are missing
		missing = missing_args(args, args.service)

		if not missing:

			# store action
			if args.action == 'store':

				# store file contents in a variable
                        	if args.file:
                                	with open(args.file, 'r') as content_file:
                                        	args.content = content_file.read()

                        	store(args)

			# retrieve action
			else:
				data = retrieve(args)

				if not args.hide:
					print(data, end=' ')

				# store data in a file
				if args.file:
					with open(args.file, 'w') as content_file:
						content_file.write(data)

		else:
			print(missing)
