import functools
import logging
import os
import shlex
import subprocess

from test.version import get_version, get_python_version

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VERSION = get_version()
__version__ = get_python_version(VERSION)

@functools.wraps(subprocess.run)
def run(args, **kwargs):
	logger = logging.getLogger('test.bambootest')
	logger.debug(shlex.join(args))
	p = subprocess.run(args, **kwargs)
	return p

def main(args):
	from test.bambootest import main

	main(args)