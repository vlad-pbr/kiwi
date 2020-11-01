#!/usr/bin/env python3

from os import listdir
from os.path import join, isdir, exists
from json import dumps

from flask import Flask, request, abort
from gevent.pywsgi import WSGIServer

app = Flask(__name__[:-3], static_url_path="/modules")

@app.route('/module/<path:module>')
def module(module):
	return "Path: " + module + " | Args: " + str(request.args)

@app.route('/api/modules')
@app.route('/api/modules/')
@app.route('/api/modules/<path:path>')
def module_api(path=''):

	# return file json
	def file_json(file_path):
		return { 
			"name": file_path.split('/')[-1],
			"type": "dir" if isdir(file_path) else "file",
			}

	abs_path = join(app.static_folder, path)

	# 404 if file does not exist
	if not exists(abs_path):
		abort(404)

	# single json for a specific file
	elif not isdir(abs_path):
		response = file_json(abs_path)

	# list of file jsons in a directory
	else:
		response = []
		for filename in listdir(abs_path):
			response.append(file_json(join(abs_path, filename)))

	return dumps(response, indent=4)

def run(kiwi):

	# server modules as static files
	app.static_folder = kiwi.Config.local_modules_dir

	http_server = WSGIServer(('', 5000), app)
	http_server.serve_forever()