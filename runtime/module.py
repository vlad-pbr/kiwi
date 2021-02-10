#!/usr/bin/env python3

import sys
from os import chdir
from os.path import join

def run(kiwi, argv, *ingress):

	# register module name
	module_name = argv[0]

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
	module = kiwi.import_module(module_name, kiwi.runtime.assets.module(module_name).local)

	# validate the module
	if not hasattr(module, 'kiwi_main'):
		kiwi.say("'{}' is not my module (missing kiwi_main() method)".format(module_name))
	else:

		# kiwi helper functions and variables
		helper = kiwi.Helper(module_name)

		# change directory to module directory
		chdir(helper.module_home)

		# run the module and log any exceptions coming from it
		try:
			return module.kiwi_main(helper, *ingress)
		except Exception:
			ex_type, module_exception, module_traceback = sys.exc_info()
			kiwi.say("module '{}' crashed with the following exception: {}".format(module_name, module_exception))
			if helper.write_crashlog(ex_type, module_exception, module_traceback):
				kiwi.say('detailed crash log can be found at {}'.format(join(helper.module_home, "crash.log")))
			
			return None
