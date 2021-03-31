#!/usr/bin/env python3

from flask import Flask
from json import dumps

app = Flask(__name__)

ENVIRONMENT = None

@app.route('/net/')
def net():

    # various client info
    return dumps({
        "external_ip": ENVIRONMENT['REMOTE_ADDR']
    })

def kiwi_main(_, ingress):

    # set request environment for net endpoint
    global ENVIRONMENT
    ENVIRONMENT = ingress.environment

    return ingress.handle(app)
    