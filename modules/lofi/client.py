#!/usr/bin/env python3

"""
Run lofi without any arguments to open a hardcoded lofi stream link.

Lofi will try to read a key=value file located at ~/.kiwi/lofi/lofi.conf. It's gonna look for the following keys:

* link: custom URL to a lofi stream to open
* key: YouTube Data v3 API key to query the YouTube search API and get the top 3 lofi streams

In case both are specified, 'link' takes priority.
"""

from subprocess import call, DEVNULL
from distutils.spawn import find_executable
from os.path import isfile, join
from requests import get
from random import randint
from sys import argv, exit

def get_url(kiwi):
	videoId = 'DWcJFNfaw9c'

	config_path = join(kiwi.module_home, kiwi.module_name + '.conf')
	if isfile(config_path):
		config_file = kiwi.parse_config(config_path)
		link = config_file.get('link')
		key = config_file.get('key')

		# link has priority
		if link:
			return link
		if key:
			videoId = get('https://www.googleapis.com/youtube/v3/search?part={}&type={}&eventType={}&order={}&q={}&maxResults={}&key={}'.format(
				'snippet', 'video', 'live', 'viewCount', 'lofi', '3', key
			)).json()['items'][randint(0, 2)]['id']['videoId']

	return 'https://www.youtube.com/watch?v=' + videoId

def kiwi_main(kiwi):

	if len(argv) > 1:
		if argv[1] in ['--help', '-h']:
			print(__doc__)
		else:
			print('lofi: use --help')

	elif find_executable("explorer.exe") is not None:
		call(["explorer.exe", get_url(kiwi) + "&\""], stdout=DEVNULL)
	elif find_executable("xdg-open") is not None:
		call(["nohup", "xdg-open", get_url(kiwi)], stdout=DEVNULL)
	else:
		print("No available browsers found.")
		exit(1)

	exit(0)