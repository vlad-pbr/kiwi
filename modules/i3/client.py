#!/usr/bin/env python3

'''
These are some of the common commands to be used with i3 keybindings and polybar displays
'''

import argparse
import math
import os
import sys
from requests import Request
from json import loads, dumps

VOLUME_CACHE_FILENAME = "VOLUME_CACHE"

def kiwi_main(kiwi):
	pass

	parser = argparse.ArgumentParser(description=kiwi.module_desc,
									 epilog=__doc__,
									 formatter_class=argparse.RawDescriptionHelpFormatter)

	subparsers = parser.add_subparsers(dest="action")
	parser.add_argument("-q", "--quiet", help="do not display any output", action="store_true")

	# system volume control
	volume_subparser = subparsers.add_parser("volume")
	volume_subparser.add_argument("-I", "--intervals", type=int, metavar="AMOUNT", help="intervals of the entire volume range")
	volume_subparser.add_argument("-s", "--sink", type=int, metavar="INDEX", help="target sink index", default=0)
	volume_subparser.add_argument("--range-symbol", type=str, metavar="SYMBOL", help="symbol that represents a unit of range", default="─")
	volume_subparser.add_argument("--value-symbol", type=str, metavar="SYMBOL", help="symbol that represents the current value of range", default="|")
	volume_control_group = volume_subparser.add_mutually_exclusive_group()
	volume_control_group.add_argument("-t", "--toggle-mute", action="store_true", help="toggle sound mute")
	volume_control_group.add_argument("-m", "--mute", action="store_true", help="mute sound")
	volume_control_group.add_argument("-u", "--unmute", action="store_true", help="unmute sound")
	volume_control_group.add_argument("-i", "--increment", type=int, metavar="PERCENTAGE", help="increment volume by specified percentage", choices=range(1, 100))
	volume_control_group.add_argument("-d", "--decrement", type=int, metavar="PERCENTAGE", help="decrement volume by specified percentage", choices=range(1, 100))

	# system information
	info_subparser = subparsers.add_parser("info")
	info_subparser.add_argument("-q", "--query", type=str, metavar="ATTRIBUTE", help="only print specific attribute")
	info_subparsers = info_subparser.add_subparsers(dest="info_action")

	# system information
	wan_subparser = info_subparsers.add_parser("wan")
	lan_subparser = info_subparsers.add_parser("lan")
	lan_subparser = info_subparsers.add_parser("ram")

	args = parser.parse_args()

	# write stdout to devnull if quiet
	stdout = sys.stdout
	devnull = open(os.devnull, 'w')
	if args.quiet:
		sys.stdout = devnull

	try:

		# system volume control
		if args.action == "volume":

			import pulsectl

			# must provide a range to print it out
			if not args.quiet:
				if not args.intervals:
					parser.error("must provide interval range if not using -q")
			else:
				args.intervals = 0

			# pulseaudio client
			with pulsectl.Pulse('client') as pulse:

				# get target sink
				target_sink = pulse.sink_list()[args.sink]

				# base off of the left channel volume
				current_volume = target_sink.volume.values[0]

				# if volume should be altered
				if args.increment or args.decrement or args.toggle_mute or args.mute or args.unmute:

					# if volume should be incremented
					if args.increment or args.decrement:

						# decide on a value
						increment_value = args.increment if args.increment else -args.decrement

						# keep target volume in range
						target_volume = current_volume + (increment_value / 100.0)
						if target_volume > 1 or target_volume < 0:
							target_volume = abs(target_volume) - (abs(target_volume) % 1)

					# mute/unmute
					else:
						
						# action related functions
						def mute(current_volume):
							with open(VOLUME_CACHE_FILENAME, 'w') as VOLUME_CACHE:
								VOLUME_CACHE.write(str(current_volume))
							return 0

						def unmute():
							if os.path.isfile(VOLUME_CACHE_FILENAME):
								with open(VOLUME_CACHE_FILENAME, 'r') as VOLUME_CACHE:
									return float(VOLUME_CACHE.read())
							return 1.0

						def toggle():

							if current_volume == 0:
								return unmute()
							else:
								return mute(current_volume)

						# act based on parameter
						if args.toggle_mute:
							target_volume = toggle()
						elif args.mute:
							target_volume = mute(current_volume)
						else:
							target_volume = unmute()

					# set result volume
					pulse.volume_set_all_chans(target_sink, target_volume)

					# update current volume value
					current_volume = target_volume

				# print volume state
				volume_range = args.range_symbol * args.intervals
				value_index = max(0, math.floor(args.intervals * current_volume) - 1)
				print(volume_range[:value_index] + args.value_symbol + volume_range[value_index + 1:])

		# networking information
		elif args.action == "info":

			import psutil

			info_json = {}

			# WAN info
			if args.info_action == "wan":
				info_json = loads(kiwi.request(Request('GET', '/info/wan')).text)

			# LAN info per NIC
			if args.info_action == "lan":
				info_json = psutil.net_if_addrs()

			# system virtual memory
			if args.info_action == "ram":
				info_json = psutil.virtual_memory()._asdict()

			# print query if specified, otherwise print everything
			if args.query:
				print(info_json.get(args.query, ""), end="")
			else:
				print(dumps(info_json, indent=4), end="")

	finally:
		sys.stdout = stdout