#!/usr/bin/env python3

from importlib.util import LazyLoader
from os import fork, getpid, listdir, kill, remove, close
from os.path import isdir, exists, isfile, dirname
from json import dumps, loads
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
import datetime
import signal

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

class Cyclops:

	class Event:
		
		def __init__(self, date):

			self.date = date

	@staticmethod
	def start_reconciler():

		# cyclops reconcile loop
		def _reconcile_loop():

			# a single reconcile with the next alarm setup
			def _reconcile(signum, stack):

				# mark loop start time
				loop_next_date = datetime.datetime.now()
				loop_next_date = loop_next_date.replace(minute=loop_next_date.minute + 1, second=0, microsecond=0)
				CYCLOPS_LOGGER.info("reconciling...")

				# reconcile
				with open(KIWI.config.local.server.cyclops.schedule, 'r') as schedule_file:
					pass # TODO reconcile logic
					
				# sleep and account for difference
				delta = loop_next_date - datetime.datetime.now()
				signal.alarm(int(delta.total_seconds()) + 1)
				CYCLOPS_LOGGER.info("next reconcile in {}s".format(delta.total_seconds()))

			# handle reconcile alarm
			signal.signal(signal.SIGALRM, _reconcile)

			# set up alarm at the start of the next minute
			next_loop = datetime.datetime.now()
			next_loop = next_loop.replace(minute=next_loop.minute + 1, second=0, microsecond=0)
			delta = next_loop - datetime.datetime.now()
			signal.alarm(int(delta.total_seconds()) + 1)
			CYCLOPS_LOGGER.info("starting reconcile loop in {}s".format(delta.total_seconds()))

			while True:
				signal.pause()

		# ensure schedule file directory
		KIWI.Helper.ensure_directory(dirname(KIWI.config.local.server.cyclops.schedule))

		# init schedule file if needed
		if not exists(KIWI.config.local.server.cyclops.schedule):

			CYCLOPS_LOGGER.info("initiating schedule file at '{}'".format(KIWI.config.local.server.cyclops.schedule))

			with open(KIWI.config.local.server.cyclops.schedule, 'w') as schedule_file:
				schedule_file.write("[]")

		if fork() == 0:
			_reconcile_loop()

KIWI = None
API = {}
ASSETS = {}
API_LOGGER = None
CYCLOPS_LOGGER = None

api = Flask(__name__[:-3] + "_api")
cyclops = Flask(__name__[:-3] + "_cyclops")

@cyclops.route('/event', methods = ['GET'])
def cyclops_create_event():
	return "It's alive!"

@api.route('/module/<module>/', methods = ['POST'])
def module(module):

	# generate request ID
	request_id = ''.join(random.choice(ascii_uppercase) for _ in range(10))

	try:

		# aknowledge request
		API_LOGGER.info("{}: received serverside request for '{}' module".format(request_id, module))

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

def start_server(apiLogHandler=logging.StreamHandler(sys.stdout), cyclopsLogHandler=logging.StreamHandler(sys.stdout)):

	# return wrapped starter function
	def _start_server():

		# gevent must be imported here as this function runs
		# after daemon fork. Since gevent creates the event loop
		# when imported, it would cause a bad interaction between
		# fork (daemon) and epoll (gevent).
		from gevent.pywsgi import WSGIServer

		def _start_component_app(component_name, component_dict, component_global_logger_name, logHandler, component_app, component_auxiliary_func=None):

			def _start():

				# define logger
				globals()[component_global_logger_name] = logging.getLogger(component_name)
				globals()[component_global_logger_name].setLevel(logging.INFO)

				# set up log handler
				logHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
				globals()[component_global_logger_name].addHandler(logHandler)

				# enable tls if specified
				ssl_args = {
					'certfile': component_dict.tls.cert,
					'keyfile': component_dict.tls.key,
					'ca_certs': component_dict.tls.ca_chain
				} if component_dict.tls.enabled else {}

				# initialize wsgi server
				listener = (component_dict.host, component_dict.port)
				server = WSGIServer(listener, component_app, log=globals()[component_global_logger_name], **ssl_args)
				globals()[component_global_logger_name].info('listening on {}:{}'.format(listener[0], listener[1]))

				# run auxiliary function for component if provided
				if component_auxiliary_func:
					component_auxiliary_func()

				# serve forever
				try:
					server.serve_forever()
				except KeyboardInterrupt:
					globals()[component_global_logger_name].warn("received keyboard interrupt")
				finally:
					globals()[component_global_logger_name].info("stopping...")

			return _start

		# run enabled components
		for component_enabled, run_component in [
			(KIWI.config.local.server.api.enabled, _start_component_app("api",
																		KIWI.config.local.server.api,
																		'API_LOGGER',
																		apiLogHandler,
																		api,
																		None)),
			(KIWI.config.local.server.cyclops.enabled, _start_component_app("cyclops",
																			KIWI.config.local.server.cyclops,
																			'CYCLOPS_LOGGER',
																			cyclopsLogHandler,
																			cyclops,
																			Cyclops.start_reconciler))
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
	if KIWI.config.local.server.daemon.foreground:
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
			KIWI.config.local.server.api.log.path,
			KIWI.config.local.server.daemon.log.path
		]:
			KIWI.Helper.ensure_directory(dirname(log_file))

		# component log handlers
		api_log_handler = logging.handlers.RotatingFileHandler(filename=KIWI.config.local.server.api.log.path,
															   maxBytes=KIWI.config.local.server.api.log.rotation.size,
															   backupCount=KIWI.config.local.server.api.log.rotation.backups)
		cyclops_log_handler = logging.handlers.RotatingFileHandler(filename=KIWI.config.local.server.cyclops.log.path,
															   maxBytes=KIWI.config.local.server.cyclops.log.rotation.size,
															   backupCount=KIWI.config.local.server.cyclops.log.rotation.backups)

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
								action=start_server(api_log_handler, cyclops_log_handler),
								logger=daemon_logger,
								keep_fds=[api_log_handler.stream.fileno(),
										  daemon_log_handler.stream.fileno(),
										  cyclops_log_handler.stream.fileno()]).start()
