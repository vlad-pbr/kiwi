#!/usr/bin/env python3

"""
Quickly play a YouTube video based on query.
This module will require a YouTube Data v3 API key to work and will prompt you for it the first time you use the module.
The module will also store this key for future use in its home directory if specified.

You can get a key by following these instructions:
https://developers.google.com/youtube/registering_an_application ('API keys' section)
"""

import argparse
from subprocess import call, DEVNULL
from distutils.spawn import find_executable
from os.path import isfile
from json import loads, dumps
from enum import Enum
from requests import get, HTTPError
from getpass import getpass
from urllib.parse import urlencode

def get_url(config):

	try:

		# build appropriate query string
		querystring = {
			"part": "snippet",
			"type": "video",
			"order": "viewCount",
			"maxResults": "1",
			"q": config[Keys.QUERY.value],
			"key": config[Keys.KEY.value]
		}

		# optional field for livestreams
		if config[Keys.LIVE.value]:
			querystring["eventType"] = "live"


		# query api
		response = get('https://www.googleapis.com/youtube/v3/search?' + urlencode(querystring))

		response.raise_for_status()
		return 'https://www.youtube.com/watch?v=' + response.json()['items'][0]['id']['videoId']

	except HTTPError as e:
		print('Received the following error while querying YouTube: {}'.format(e.__str__()))
		exit(1)

	except IndexError:
		print('No results for given query')
		exit(0)

# valid config keys
class Keys(Enum):
	KEY = "key"
	LIVE = "live"
	QUERY = "query"

def load_config(config_path):

	if isfile(config_path):
		with open(config_path, 'r') as config_file:
			return loads(config_file.read())

	return {}

def save_config(config_path, config_dict):

	with open(config_path, 'w') as config_file:
		config_file.write(dumps(config_dict, indent=4))

def kiwi_main(kiwi):

	parser = argparse.ArgumentParser(description=kiwi.module_desc,
									 epilog=__doc__,
									 formatter_class=argparse.RawDescriptionHelpFormatter)

	parser.add_argument('-q', '--query', type=str, required=True)
	parser.add_argument('-l', '--live', action='store_true')
	parser.add_argument('-k', '--key', type=str)
	parser.add_argument('-s', '--save-key', action='store_true')

	args = parser.parse_args()

	config_path = 'youtube.json'
	config = load_config(config_path)

	if not args.key:

		# if key not stored and not passed as argument
		if Keys.KEY.value not in config:
			print("A YouTube Data v3 API key is required to query the API")
			print("You can get a key by following these instructions:")
			print("https://developers.google.com/youtube/registering_an_application ('API keys' section)")
			config[Keys.KEY.value] = getpass("API key (output is hidden): ")

			if args.save_key or kiwi.ask("Save key for future use?", ['y', 'n']) == 'y':
				save_config(config_path, config)

	# use provided key and store if specified
	else:
		config[Keys.KEY.value] = args.key

		if args.save_key:
			save_config(config_path, config)

	# append required fields to current config
	for key, value in [ 
		(Keys.QUERY.value, args.query),
		(Keys.LIVE.value, args.live)
	]:
		config[key] = value

	# find appropriate executable
	if find_executable("explorer.exe") is not None:
		call(["explorer.exe", get_url(config) + "&\""], stdout=DEVNULL)
	elif find_executable("xdg-open") is not None:
		call(["nohup", "xdg-open", get_url(config)], stdout=DEVNULL)
	else:
		print("No available browsers found.")
		exit(1)

	exit(0)