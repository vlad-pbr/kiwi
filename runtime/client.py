#!/usr/bin/env python3

import os
import sys
import requests

def bulleted_list(preface, items):
	
	list_ = preface

	# format each item in bullet form
	for item in items:
		list_ += "\n\t* {}".format(item)

	return list_

def run(kiwi, args):

	# list modules
	if args.list_modules:
		installed = kiwi.get_installed_module_list()
			
		# try getting remote module list
		try:
			modules = kiwi.get_remote_module_list()
		except requests.exceptions.RequestException:
			kiwi.say("could not reach remote to fetch module list, listing local modules only")
			modules = installed[:]

		# compare modules and mark as installed
		for module in modules:
			print('[{}] {}: {}'.format('x' if module in installed else ' ', module, kiwi.get_module_description(module)))
			if module in installed:
				installed.remove(module)

		# list unknown modules
		for module in installed:
			print('[{}] {}: {}'.format('?', module, kiwi.get_module_description(module)))

	# fetching and updating modules have the same logic behind them
	if args.get_modules is not None or args.update_modules is not None:
		modules = args.get_modules if args.get_modules is not None else args.update_modules

		# fetching / updating all modules
		if not len(modules):
				
			# collect remote module list if fetching, local list if updating
			if args.get_modules is not None:
				try:
					modules = kiwi.get_remote_module_list()
				except requests.exceptions.RequestException:
					kiwi.say("could not reach remote to fetch module list")
					sys.exit(1)
			else:
				modules = kiwi.get_installed_module_list()

		# fetch / update collected modules
		modules_fetched, modules_update, modules_failed = kiwi.fetch_modules(modules, args.update_modules != None)

		# fetch results
		if args.get_modules:
			kiwi.say(bulleted_list('fetch results', [
				'{} new modules fetched'.format(len(modules_fetched)),
				'{} modules could not be fetched'.format(len(modules_failed)),
				'{} modules have an available update'.format(len(modules_update)),
				'{} modules are present and up to date'.format(len(modules) - len(modules_fetched) - len(modules_update) - len(modules_failed))
			]))
	
		# update outdated modules if need be
		if len(modules_update) > 0:
			if kiwi.Helper.ask('\nUpdate the outdated modules?', ['y', 'n'], 'y' if args.yes else None) == 'y':
				modules_fetched, _, modules_failed = kiwi.fetch_modules(modules_update, True)
			else:
				sys.exit(0)

		# update results
		if args.update_modules or len(modules_update) > 0:
			kiwi.say(bulleted_list('update results', [
				'{} modules were updated'.format(len(modules_fetched)),
				'{} modules could not be updated'.format(len(modules_failed))
			]))
	
	# kiwi self update
	if args.self_update:

		if kiwi.runtime.update("I have an update", args.yes):
			kiwi.say("I'm up to date")

	# dump current configuration to file
	if args.dump_config:
		with open(args.dump_config, 'w') as config_file:
			config_file.write(kiwi.config.dump())

		kiwi.say("dumped current configuration to '{}'".format(args.dump_config))

	# start kiwi server
	if args.start_server:
		return kiwi.runtime.run(kiwi.runtime.Modules.Server, kiwi)

	# run kiwi module
	if args.module:
		return kiwi.run_module(args.module[0], " ".join(args.module[1:]), client=(not args.server), foreground=True)
