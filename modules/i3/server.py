#!/usr/bin/env python3

from flask import Flask
from json import dumps

app = Flask(__name__)

EXTERNAL_REQUEST = None

@app.route('/net/')
def net():

    # various client info
    return dumps({
        "external_ip": EXTERNAL_REQUEST.environ['REMOTE_ADDR']
    })

def kiwi_main(_, ingress):

    # set external request global for net endpoint
    global EXTERNAL_REQUEST
    EXTERNAL_REQUEST = ingress.external_request

    return ingress.handle(app)
    