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
import random
from string import ascii_uppercase

from flask import Flask, request, abort, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.serving import run_simple

import jsonpickle

class ServerHelper:

	class Ingress:

		def __init__(self, request, environment):
			self.request = request
			self.environment = environment
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
			try:
				close(self.socket_fd)
				remove(self.socket_path)
			except OSError:
				pass

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

	def __init__(self, request, environment):
		self.ingress = self.Ingress(request, environment)

	def __del__(self):
		self.ingress.__del__()

KIWI = None
API = {}
ASSETS = {}
API_LOGGER = None

api = Flask(__name__[:-3])

@api.route('/module/<module>/', methods = ['POST'])
def module(module):

	# generate request ID
	request_id = ''.join(random.choice(ascii_uppercase) for _ in range(10))
	API_LOGGER.info("{}: received serverside request for '{}' module".format(request_id, module))

	try:

		# various server helpers
		API_LOGGER.info("{}: preparing server helpers".format(request_id))
		serverHelper = ServerHelper(jsonpickle.decode(request.get_json()), request.environ.copy())

		# get response from serverside module
		API_LOGGER.info("{}: running '{}' serverside".format(request_id, module))
		response = KIWI.run_module(module, "", serverHelper, client=False)

		# finalize server helper object
		API_LOGGER.info("{}: finalizing server helpers".format(request_id))
		serverHelper.__del__()

		# response is not allowed to be None
		if response is None:
			API_LOGGER.error("{}: empty response received from '{}' serverside".format(request_id, module))
			abort(500)

		# return serialized response object
		API_LOGGER.info("{}: serializing response".format(request_id))
		return jsonpickle.encode(response)

	except HTTPException as e:
		API_LOGGER.error("{}: HTTP error: {}".format(request_id, e.__str__()))
		raise
	except:
		API_LOGGER.error("{}: unknown kiwi serverside exception".format(request_id))
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

@api.route('/api/<asset>/')
@api.route('/api/<asset>/<path:path>')
def serve_api(asset, path=''):
	return API[asset](path) if asset in API else abort(404)

@api.route('/assets/<asset>/<path:path>')
def serve_asset(asset, path):
	return ASSETS[asset](path) if asset in ASSETS else abort(404)

@api.route('/assets/kiwi/')
def serve_kiwi():
	return kiwi_asset()

def start_server(apiLogHandler=logging.StreamHandler(sys.stdout)):

	# return wrapped starter function
	def _start_server():

		def _start_api():

			global API_LOGGER

			# gevent must be imported here as this function runs
			# after daemon fork. Since gevent creates the event loop
			# when imported, it would cause a bad interaction between
			# fork (daemon) and epoll (gevent).
			from gevent.pywsgi import WSGIServer

			# define logger
			API_LOGGER = logging.getLogger(KIWI.Config.kiwi_name)
			API_LOGGER.setLevel(logging.INFO)

			# set up log handler
			apiLogHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
			API_LOGGER.addHandler(apiLogHandler)

			# enable tls if specified
			ssl_args = {
				'certfile': KIWI.config.local.server.api.tls.cert,
				'keyfile': KIWI.config.local.server.api.tls.key,
				'ca_certs': KIWI.config.local.server.api.tls.ca_chain
			} if KIWI.config.local.server.api.tls.enabled else {}

			# initialize wsgi server
			api_listener = (KIWI.config.local.server.api.host, KIWI.config.local.server.api.port)
			api_server = WSGIServer(api_listener, api, log=API_LOGGER, **ssl_args)
			API_LOGGER.info('listening on {}:{}'.format(api_listener[0], api_listener[1]))

			try:
				api_server.serve_forever()
			except KeyboardInterrupt:
				API_LOGGER.warn("received keyboard interrupt")
			finally:
				API_LOGGER.info("stopping server...")

		# run enabled components
		for component_enabled, run_component in [
			(KIWI.config.local.server.api.component.enabled, _start_api)
		]:
			if component_enabled:
				Thread(target=run_component, daemon=False).start()

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
	if KIWI.config.local.server.api.foreground:
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
			KIWI.config.local.server.api.component.log.path,
			KIWI.config.local.server.daemon.log.path
		]:
			KIWI.Helper.ensure_directory(dirname(log_file))

		# api log handler
		api_log_handler = logging.handlers.RotatingFileHandler(filename=KIWI.config.local.server.api.component.log.path,
															   maxBytes=KIWI.config.local.server.api.component.log.rotation.size,
															   backupCount=KIWI.config.local.server.api.component.log.rotation.backups)

		# daemon logger setup
		daemon_logger = logging.getLogger("daemon")
		daemon_logger.setLevel(logging.INFO)
		daemon_log_handler = logging.handlers.RotatingFileHandler(filename=KIWI.config.local.server.daemon.log.path,
															   	  maxBytes=KIWI.config.local.server.daemon.log.rotation.size,
															   	  backupCount=KIWI.config.local.server.daemon.log.rotation.backups)
		daemon_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
		daemon_logger.addHandler(daemon_log_handler)

		# start daemon
		KIWI.say('starting daemon...')
		Daemonize(app=__name__, pid=pid_file_path,
								action=start_server(api_log_handler),
								logger=daemon_logger,
								keep_fds=[api_log_handler.stream.fileno(), daemon_log_handler.stream.fileno()]).start()
