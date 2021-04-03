#!/usr/bin/env python3

# This is how a basic serverside kiwi module functions.
#
# A problem arises when you consider that each module can have a backend.
# And each backend is unique to the request.
# And there can be virtually thousands of backends.
# On the same kiwi host.
#
# In order to solve this problem, kiwi provides a helper ingress object.
# It accepts a WSGI app, starts it on a UNIX socket and runs the request against it.
# The resulting response object can be safely returned to the client.

from socket import gethostname
from flask import Flask, request

app = Flask(__name__)

@app.route('/')
def greet():

    # check if name is specified in query args
    name = request.args.get("name", default=None)

    # return greeting
    return 'Hello from {}{}!'.format(gethostname(), (', ' + name) if name is not None else '')

def kiwi_main(kiwi, helper):

    kiwi.logger.info("Received greeting!")

    # let helper ingress object take care of the request based on given app
    return helper.ingress.handle(app)
    