#!/usr/bin/env python2
kiwi_description = 'Open a new browser window with a lofi music stream'

import distutils.spawn
import subprocess
from requests import get
from random import randint

# pre generated key configured to only query the YouTube Data API (from home)
key = 'AIzaSyCFbq79LHDA2eoOeb_BPjWZSjQOCYFw6K0'
videoId = get('https://www.googleapis.com/youtube/v3/search?part={}&type={}&eventType={}&order={}&q={}&maxResults={}&key={}'.format(
	'snippet', 'video', 'live', 'viewCount', 'lofi', '3', key
)).json()['items'][randint(0, 2)]['id']['videoId']
lofi_url = "https://www.youtube.com/watch?v=" + str(videoId)

def kiwi_main():
	if distutils.spawn.find_executable("explorer.exe") is not None:
		subprocess.call(["explorer.exe", lofi_url + "&\""])
	elif distutils.spawn.find_executable("xdg-open") is not None:
		subprocess.call(["xdg-open", lofi_url])
	else:
		print "No available browsers found."
