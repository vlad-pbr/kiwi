#!/usr/bin/env python2

"""
Single oscillator that can generate a wave at a given frequency for a given duration.
I plan on adding more voices of choice, maybe even filters.
"""

import argparse
import soundfile as sf
from math import sin, pi, log10
from random import random, seed

def waveform_decorator():

	"""Registering decorator for waveforms"""

	waveforms_list = []

	def registrar(func):
		waveforms_list.append(func.__name__)
		return func

	registrar.list = waveforms_list
	return registrar

waveform = waveform_decorator()
sample_rate = 44100
seed(1)

def percent_to_dB(percent):
	return 10 * log10(percent**2)

@waveform
def noise(val):
	return random()

@waveform
def square(val):
	return 1.0 if val % (pi * 2) <= pi else -1.0

@waveform
def triangle(val):
	return ((val % (pi * 2)) / (pi / 2)) - 1 if val % (pi * 2) <= pi else 1 - ((val % pi) / (pi / 2))

@waveform
def sine(val):
	return sin(val)	

@waveform
def saw(val):
	return ((val % (pi * 2)) / pi) - 1

def kiwi_main():

	"""Oscillate a wave with given parameters"""

	parser = argparse.ArgumentParser(description=kiwi_main.__doc__, epilog=__doc__)

	parser.add_argument('-f', '--frequency', help='oscillation frequency (Hz)', type=int, required=True)
	parser.add_argument('-w', '--waveform', help='oscillation waveform', choices=waveform.list, required=True)
	parser.add_argument('-s', '--seconds', help='oscillation duration in seconds', default=1, type=int)
	parser.add_argument('-d', '--destination', help='oscillation file destination', type=str, required=True)

	args = parser.parse_args()

	# write samples to array
	samples = []

	for i in range(sample_rate):
		samples.append(globals()[args.waveform]((pi * 2 * args.frequency) * (float(i) / sample_rate)))
	samples *= args.seconds
	
	# write to disk
	sf.write(args.destination, samples, sample_rate)
