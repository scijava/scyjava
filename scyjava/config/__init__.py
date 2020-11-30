import logging
import pathlib
import jpype

_logger = logging.getLogger(__name__)

_endpoints = []
_repositories = {1: 'https://maven.scijava.org/content/repositories/releases'}
_verbose = 0
_manage_deps = True
_cache_dir = pathlib.Path.home() / '.jgo'
_m2_repo = pathlib.Path.home() / '.m2' / 'repository'
_options = []


def maven_scijava_repository():
    """
    :return: url for public scijava maven repo
    """
    return 'https://maven.scijava.org/content/groups/public'


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


def set_manage_deps(manage):
    global _manage_deps
    _logger.debug('Setting manage deps to %d (was %d)', manage, _manage_deps)
    _manage_deps = manage


def get_manage_deps():
    global _manage_deps
    return _manage_deps


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


def add_classpath(*path):
    jpype.addClassPath(*path)


def get_classpath():
    return jpype.getClassPath()


def add_option(option):
    global _options
    _options.append(option)


def add_options(options):
    global _options
    _options.extend(options)


def get_options():
    global _options
    return _options
