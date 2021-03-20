#!/usr/bin/env python3

from flask import Flask, request
from json import dumps

app = Flask(__name__)

@app.route('/net/')
def net():

    # various client info
    return dumps({
        "external_ip": request.environ['REMOTE_ADDR']
    })

def kiwi_main(_, ingress):
    return ingress.handle(app)
    