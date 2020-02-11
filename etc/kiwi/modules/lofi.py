#!/usr/bin/env python2

from subprocess import call
from distutils.spawn import find_executable
from os.path import isfile
from requests import get
from random import randint

def get_url(kiwi):
	videoId = 'hHW1oY26kxQ'

	if isfile(kiwi['module_home'] + kiwi['module_name'] + '.conf'):
		config_file = kiwi['parse_config'](kiwi['module_home'] + kiwi['module_name'] + '.conf')
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

	"""Open a new browser window with a lofi music stream"""

	if find_executable("explorer.exe") is not None:
		call(["explorer.exe", get_url(kiwi) + "&\""])
	elif find_executable("xdg-open") is not None:
		call(["xdg-open", get_url(kiwi)])
	else:
		print "No available browsers found."
