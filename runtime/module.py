#!/usr/bin/env python2

import sys
from os import chdir
from os.path import join
from imp import load_source

def run(kiwi, argv):

	# register module name, drop kiwi from arguments
	module_name = argv[1]
	argv.pop(0)

	# if module is not installed - see if it exists on remote
	if module_name not in kiwi.get_installed_module_list():
		if module_name not in kiwi.get_remote_module_list():
			kiwi.say("I don't have a module called '{}' :(".format(module_name))
			sys.exit(1)
		
		# fetch the module
		else:
			module_as_list = list()
			module_as_list.append(module_name)
			_, _, modules_failed = kiwi.fetch_modules(module_as_list)
			if modules_failed:
				sys.exit(1)
				
	# import module code
	module = load_source(module_name, join(kiwi.Config.kiwi_local_modules_dir, module_name, 'client.py'))

	# validate the module
	if not hasattr(module, 'kiwi_main'):
		kiwi.say("'{}' is not my module (missing kiwi_main() method)".format(module_name))
	else:
			
		# resolve dependencies
		if hasattr(module, 'kiwi_dependencies'):
			dependencies = set(module.kiwi_dependencies) - set(kiwi.get_installed_module_list())
			if dependencies:
				_, _, modules_failed = kiwi.fetch_modules(dependencies)
				if modules_failed:
					kiwi.say('could not resolve the following dependencies: {}'.format(', '.join(modules_failed)))
					print "Possible solutions:"
					print "\t* sudo kiwi -g {}".format(' '.join(modules_failed))
					sys.exit(1)

		# inject kiwi helper functions and variables
		module.__dict__['kiwi'] = kiwi.Helper(module_name)

		# change directory to module directory
		chdir(module.kiwi.module_home)

		# run the module and log any exceptions coming from it
		try:
			rc = module.kiwi_main()
			sys.exit(rc if isinstance(rc, int) else 0)
		except Exception:
			ex_type, module_exception, module_traceback = sys.exc_info()
			kiwi.say("module '{}' crashed with the following exception: {}".format(module_name, module_exception))
			if module.kiwi.write_crashlog(crash_log_path, ex_type, module_exception, module_traceback):
				kiwi.say('detailed crash log can be found at {}'.format(crash_log_path))
			sys.exit(1)
