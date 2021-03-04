#!/usr/bin/env python3

from os import listdir, kill, remove, close
from os.path import isdir, exists, isfile, realpath, dirname
from json import dumps
from multiprocessing import Process
from daemonize import Daemonize
from tempfile import mkstemp
from requests_unixsocket import Session
from requests.exceptions import ConnectionError
from urllib.parse import quote
from threading import Thread
from time import sleep

from flask import Flask, request, abort, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.serving import run_simple

import jsonpickle

class Ingress:

	def __init__(self, request):
		self.request = request
		self.socket_fd, self.socket_path = mkstemp()

		# take care of slash edge cases
		if self.request.url:
			self.request.url = self.request.url if request.url[0] != '/' else self.request.url[1:]
		else:
			self.request.url = ''

		# set url to unix socket and prepare
		request.url = "http+unix://{}/{}".format(quote(self.socket_path, safe=''), request.url)
		self.request = request.prepare()

	def __del__(self):
		close(self.socket_fd)
		remove(self.socket_path)

	def handle(self, app):

		# run server on unix socket
		def run_server():
			run_simple("unix://{}".format(self.socket_path), port=8080, application=app)
		Thread(target=run_server, daemon=True).start()

		# new socket session
		socket_session = Session()

		# query socket until received a valid response
		while True:
			try:
				return socket_session.send(request=self.request)
			except ConnectionError:
				sleep(0.1)
			except:
				return None
			finally:
				socket_session.close()

KIWI = None
API = {}
ASSETS = {}

app = Flask(__name__[:-3])

@app.route('/module/<module>/', methods = ['POST'])
def module(module):
	try:

		# new ingress object for received request
		ingress = Ingress(jsonpickle.decode(request.get_json()))

		# get response from serverside module
		response = KIWI.runtime.run(KIWI.runtime.Modules.Module, KIWI, [ module ], ingress )

		# finalize ingress object
		ingress.__del__()

		# response is not allowed to be None
		if response is None:
			abort(500)

		# return serialized response object
		return jsonpickle.encode(response)

	except HTTPException:
		raise
	except:
		abort(500)

def runtime_json(path):
	return assets_json(KIWI.config.local.client.runtime_dir, path)

def runtime_asset(path):
	return send_from_directory(KIWI.config.local.client.runtime_dir, path)

def modules_json(path):
	return assets_json(KIWI.config.local.client.modules_dir, path)

def modules_asset(path):
	return send_from_directory(KIWI.config.local.client.modules_dir, path)

def kiwi_asset():
	return send_from_directory(KIWI.config.local.client.runtime_dir, 'kiwi')

def assets_json(source, path):
	
	# return file json
	def file_json(file_path):
		return { 
			"name": file_path.split('/')[-1],
			"type": "dir" if isdir(file_path) else "file",
			}

	abs_path = KIWI.Helper.join(source, path)

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
			response.append(file_json(KIWI.Helper.join(abs_path, filename)))

	return dumps(response, indent=4)

@app.route('/api/<asset>/')
@app.route('/api/<asset>/<path:path>')
def serve_api(asset, path=''):
	return API[asset](path) if asset in API else abort(404)

@app.route('/assets/<asset>/<path:path>')
def serve_asset(asset, path):
	return ASSETS[asset](path) if asset in ASSETS else abort(404)

@app.route('/assets/kiwi/')
def serve_kiwi():
	return kiwi_asset()

def start_server():
	from gevent.pywsgi import WSGIServer

	http_server = WSGIServer(('', int(KIWI.config.local.server.port)), app)
	http_server.serve_forever()

def run(kiwi):

	pid_file_path = kiwi.Helper.join(kiwi.config.local.home_dir, 'PID')

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
					kiwi.say('stopping server...')

					# kill daemon and remove PID file
					kill(pid, 9)
					remove(pid_file_path)

					exit(0)

	global KIWI
	global API
	global ASSETS

	KIWI = kiwi

	# api endpoints
	API = {
		"modules": modules_json,
		"runtime": runtime_json
	}

	# asset endpoints
	ASSETS = {
		"modules": modules_asset,
		"runtime": runtime_asset
	}

	KIWI.say('starting server...')

	# start server process
	server = Daemonize(app=__name__, pid=pid_file_path, action=start_server)
	server.start()
