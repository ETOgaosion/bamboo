import argparse
import logging
import os
import time

import project_pactum

from colorama import Fore, Style

logger = logging.getLogger(__name__)

class ProjectPactumFormatter(logging.Formatter):

	def __init__(self):
		self.created = time.time()

	def format(self, record):
		reltime = record.created - self.created
		COLORS = {
			logging.DEBUG: 35,
			logging.INFO: 36,
			logging.WARNING: 33,
			logging.ERROR: 31,
		}
		fmt = '\x1B[1;{color}m[{reltime:.3f} p%(process)d/t%(thread)d %(levelname)s %(name)s]\x1B[m \x1B[{color}m%(message)s\x1B[m'
		formatter = logging.Formatter(fmt.format(color=COLORS[record.levelno], reltime=reltime))
		return formatter.format(record)

def parse(args):
	parser = argparse.ArgumentParser(prog='project_pactum',
	                                 description='Project Pactum')

	parser.add_argument(
		'--version', action='version',
		version=f'{Fore.BLUE}{Style.BRIGHT}Bamboo{Style.RESET_ALL}'
		        f' {Style.BRIGHT}{project_pactum.__version__}{Style.RESET_ALL}')

	return parser.parse_args(args)

def setup_logging():
	stream_handler = logging.StreamHandler()
	stream_handler.setFormatter(ProjectPactumFormatter())
	logging.basicConfig(level=logging.DEBUG, handlers=[stream_handler])

	if 'PROJECT_PACTUM_LOGGING_INFO' in os.environ:
		for p in os.environ['PROJECT_PACTUM_LOGGING_INFO'].split(','):
			logging.getLogger(p).setLevel(logging.INFO)

	logging.getLogger('botocore.auth').setLevel(logging.INFO)
	logging.getLogger('botocore.client').setLevel(logging.INFO)
	logging.getLogger('botocore.credentials').setLevel(logging.INFO)
	logging.getLogger('botocore.endpoint').setLevel(logging.INFO)
	logging.getLogger('botocore.handlers').setLevel(logging.INFO)
	logging.getLogger('botocore.hooks').setLevel(logging.INFO)
	logging.getLogger('botocore.httpsession').setLevel(logging.INFO)
	logging.getLogger('botocore.loaders').setLevel(logging.INFO)
	logging.getLogger('botocore.parsers').setLevel(logging.INFO)
	logging.getLogger('botocore.retryhandler').setLevel(logging.INFO)
	logging.getLogger('botocore.utils').setLevel(logging.INFO)
	logging.getLogger('boto3.resources.action').setLevel(logging.INFO)
	logging.getLogger('boto3.resources.collection').setLevel(logging.INFO)
	logging.getLogger('boto3.resources.factory').setLevel(logging.INFO)
	logging.getLogger('boto3.resources.model').setLevel(logging.INFO)

	logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)

	logging.getLogger('matplotlib').setLevel(logging.INFO)
