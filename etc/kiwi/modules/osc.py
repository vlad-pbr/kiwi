#!/usr/bin/env python2
#kiwidesc=oscillates a wave with given parameters

import argparse
import soundfile as sf
from math import sin, pi, log10
from random import random, seed

waveforms=['sine', 'saw', 'triangle', 'square', 'noise']
sample_rate = 44100
seed(1)

def percent_to_dB(percent):
	return 10 * log10(percent**2)

def noise(val):
	return random()

def square(val):
	return 1.0 if val % (pi * 2) <= pi else -1.0

def triangle(val):
	return ((val % (pi * 2)) / (pi / 2)) - 1 if val % (pi * 2) <= pi else 1 - ((val % pi) / (pi / 2))

def sine(val):
	return sin(val)	

def saw(val):
	return ((val % (pi * 2)) / pi) - 1

def kiwi_main():
	parser = argparse.ArgumentParser('Generate oscillations!')

	parser.add_argument('-f', '--frequency', help='oscillation frequency (Hz)', type=int, required=True)
	parser.add_argument('-w', '--waveform', help='oscillation waveform', choices=waveforms, required=True)
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
