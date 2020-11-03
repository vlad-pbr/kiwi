#!/usr/bin/env python3

from os import listdir, kill, remove
from os.path import join, isdir, exists, isfile
from json import dumps
from multiprocessing import Process
from daemonize import Daemonize

from flask import Flask, request, abort, send_from_directory
from werkzeug.exceptions import HTTPException
from gevent.pywsgi import WSGIServer

kiwi = None
api = {}
assets = {}

app = Flask(__name__[:-3])

@app.route('/module/<module>/')
@app.route('/module/<module>/<path:path>')
def module(module, path=''):
	try:
		response = kiwi.runtime.run(kiwi.runtime.Modules.Module, kiwi, [ module, path ])
		
		return response if response is not None else abort(500)
	except HTTPException:
		raise
	except:
		abort(500)

def runtime_json(path):
	return assets_json(kiwi.Config.local_runtime_dir, path)

def runtime_asset(path):
	return send_from_directory(kiwi.Config.local_runtime_dir, path)

def modules_json(path):
	return assets_json(kiwi.Config.local_modules_dir, path)

def modules_asset(path):
	return send_from_directory(kiwi.Config.local_modules_dir, path)

def assets_json(source, path):
	
	# return file json
	def file_json(file_path):
		return { 
			"name": file_path.split('/')[-1],
			"type": "dir" if isdir(file_path) else "file",
			}

	abs_path = join(source, path)

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

@app.route('/api/<asset>/')
@app.route('/api/<asset>/<path:path>')
def serve_api(asset, path=''):
	return api[asset](path) if asset in api else abort(404)

@app.route('/assets/<asset>/<path:path>')
def serve_asset(asset, path):
	return assets[asset](path) if asset in assets else abort(404)

def run(_kiwi):

	pid_file_path = join(_kiwi.Config.home_dir, 'PID')

	# open PID file
	if isfile(pid_file_path):
		with open(pid_file_path, 'r') as pid_file:
			pid = int(pid_file.read())

			# if server is already running
			if pid:
				try:
					kill(pid, 0)
				except OSError:
					pass
				else:
					_kiwi.say('stopping server...')

					# kill daemon and remove PID file
					kill(pid, 9)
					remove(pid_file_path)

					exit(0)

	global kiwi
	global api
	global assets

	kiwi = _kiwi

	# api endpoints
	api = {
		"modules": modules_json,
		"runtime": runtime_json
	}

	# asset endpoints
	assets = {
		"modules": modules_asset,
		"runtime": runtime_asset
	}

	_kiwi.say('starting server...')

	# toggle server process
	http_server = WSGIServer(('', int(_kiwi.Config.server_port)), app)
	server_daemon = Daemonize(app=app.import_name, pid=pid_file_path, action=http_server.serve_forever)
	server_daemon.start()
