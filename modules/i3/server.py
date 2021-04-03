#!/usr/bin/env python3

from flask import Flask
from json import dumps

app = Flask(__name__)

ENVIRONMENT = None

@app.route('/info/wan')
def net():

    # various client info
    return dumps({
        "ip": ENVIRONMENT['REMOTE_ADDR']
    })

def kiwi_main(_, helper):

    # set request environment for net endpoint
    global ENVIRONMENT
    ENVIRONMENT = helper.ingress.environment

    return helper.ingress.handle(app)
    