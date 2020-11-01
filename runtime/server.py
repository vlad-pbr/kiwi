#!/usr/bin/env python3

from flask import Flask, request
from gevent.pywsgi import WSGIServer

app = Flask(__name__[:-3], static_url_path="/modules")

@app.route('/module/<path:module>')
def module(module):
	return "Path: " + module + " | Args: " + str(request.args)

def run(kiwi):

	# serve modules as static files
	app.static_folder = kiwi.Config.kiwi_local_modules_dir

	http_server = WSGIServer(('', 5000), app)
	http_server.serve_forever()