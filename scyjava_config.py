__all__ = (
    'maven_scijava_repository',
    'add_endpoints',
    'get_endpoints',
    'add_repositories',
    'get_repositories',
    'set_verbose',
    'get_verbose',
    'set_cache_dir',
    'get_cache_dir',
    'set_m2_repo',
    'get_m2_repo',
    'set_options',
    'add_options',
    'get_options',
    'set_classpath',
    'add_classpath',
    'get_classpath',
    'expand_classpath')

import logging
import jnius_config
import pathlib

version = '0.1.0'

_logger = logging.getLogger(__name__)

_endpoints    = []
_repositories = {}
_verbose      = 0
_cache_dir    = pathlib.Path.home() / '.jgo'
_m2_repo      = pathlib.Path.home() / '.m2' / 'repository'

def maven_scijava_repository():
    """
    :return: url for public scijava maven repo
    """
    return 'https://maven.imagej.net/content/groups/public'

def add_endpoints(*endpoints):
    global _endpoints
    _logger.debug('Adding endpoints %s to %s', endpoints, _endpoints)
    _endpoints.extend(endpoints)


def get_endpoints():
    global _endpoints
    return _endpoints


def add_repositories(*args, **kwargs):
    global _repositories
    for arg in args:
        _logger.debug('Adding repositories %s to %s', arg, _repositories)
        _repositories.update(arg)
    _logger.debug('Adding repositories %s to %s', kwargs, _repositories)
    _repositories.update(kwargs)


def get_repositories():
    global _repositories
    return _repositories


def set_verbose(level):
    global _verbose
    _logger.debug('Setting verbose level to %d (was %d)', level, _verbose)
    _verbose = level


def get_verbose():
    global _verbose
    _logger.debug('Getting verbose level: %d', _verbose)
    return _verbose


def set_cache_dir(dir):
    global _cache_dir
    _logger.debug('Setting cache dir to %s (was %s)', dir, _cache_dir)
    _cache_dir = dir


def get_cache_dir():
    global _cache_dir
    return _cache_dir


def set_m2_repo(dir):
    global _m2_repo
    _logger.debug('Setting m2 repo dir to %s (was %s)', dir, _m2_repo)
    _m2_repo = dir


def get_m2_repo():
    global _m2_repo
    return _m2_repo


# directly delegating to jnius_config
def add_classpath(*path):
    jnius_config.add_classpath(*path)


def set_classpath(*path):
    jnius_config.set_classpath(*path)


def get_classpath():
    return jnius_config.get_classpath()


def add_options(*opts):
    jnius_config.add_options(*opts)


def set_options(*opts):
    jnius_config.set_options(*opts)


def get_options():
    return jnius_config.get_options()


def expand_classpath():
    return jnius_config.expand_classpath()

