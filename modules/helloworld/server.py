#!/usr/bin/env python3

from socket import gethostname

def kiwi_main(kiwi):
    return 'Hello from {}!'.format(gethostname())
    