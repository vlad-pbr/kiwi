#!/usr/bin/env python3

from flask import Flask, request

app = Flask(__name__[:-3], static_url_path="/modules")

@app.route('/module/<path:module>')
def module(module):
	return "Path: " + module + " | Args: " + str(request.args)

def run(kiwi):

	# server modules as static files
	app.static_folder = kiwi.Config.kiwi_local_modules_dir

	app.run(host="0.0.0.0")