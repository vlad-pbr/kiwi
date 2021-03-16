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

import logging
import sys

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
		response = KIWI.run_module(module, "", ingress, client=False)

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

def start_server(logHandler=logging.StreamHandler(sys.stdout)):

	# define logger
	api_logger = logging.getLogger(KIWI.Config.kiwi_name)
	api_logger.setLevel(logging.INFO)

	# set up log handler
	logHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
	api_logger.addHandler(logHandler)

	# return wrapped starter function
	def _start_server():

		# gevent must be imported here as this function runs
		# after daemon fork. Since gevent creates the event loop
		# when imported, it would cause a bad interaction between
		# fork (daemon) and epoll (gevent).
		from gevent.pywsgi import WSGIServer

		# initialize wsgi server
		listener = (KIWI.config.local.server.host, KIWI.config.local.server.port)
		server = WSGIServer(listener, app, log=api_logger)

		api_logger.info('listening on {}:{}'.format(listener[0], listener[1]))

		try:
			server.serve_forever()
		except KeyboardInterrupt:
			api_logger.warn("received keyboard interrupt")
		finally:
			api_logger.info("stopping server...")

	return _start_server

def run(kiwi):

	global KIWI, API, ASSETS

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

	# foreground
	if KIWI.config.local.server.foreground:
		start_server()()

	# background
	else:

		pid_file_path = KIWI.Helper.join(KIWI.config.local.home_dir, 'PID')

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
						KIWI.say('stopping daemon...')

						# terminate daemon and remove PID file
						kill(pid, 15)
						remove(pid_file_path)

						exit(0)

		# ensure log folders
		for log_file in [
			KIWI.config.local.server.log.api.path
		]:
			KIWI.Helper.ensure_directory(dirname(log_file))

		# api log handler
		api_log_handler = logging.handlers.RotatingFileHandler(filename=KIWI.config.local.server.log.api.path,
															   maxBytes=KIWI.config.local.server.log.api.size,
															   backupCount=KIWI.config.local.server.log.api.backups)

		# daemon logger setup
		daemon_logger = logging.getLogger("daemon")
		daemon_logger.setLevel(logging.INFO)
		daemon_logger.addHandler(api_log_handler)

		# start daemon
		KIWI.say('starting daemon...')
		Daemonize(app=__name__, pid=pid_file_path,
								action=start_server(api_log_handler),
								logger=daemon_logger,
								keep_fds=[api_log_handler.stream.fileno()]).start()
