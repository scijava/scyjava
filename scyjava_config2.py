__all__ = (
    'maven_scijava_repository',
    'add_endpoints',
    'get_endpoints',
    'add_repositories',
    'get_repositories',
    'set_verbose',
    'get_verbose',
    'set_manage_deps',
    'get_manage_deps',
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
import pathlib

version = '0.4.1.dev1'

_logger = logging.getLogger(__name__)

_endpoints    = []
_repositories = {}
_verbose      = 0
_manage_deps  = True
_cache_dir    = pathlib.Path.home() / '.jgo'
_m2_repo      = pathlib.Path.home() / '.m2' / 'repository'

def maven_scijava_repository():
    """
    :return: url for public scijava maven repo
    """
    return 'https://maven.scijava.org/content/groups/public'

def add_repositories(*args, **kwargs):
    global _repositories
    for arg in args:
        _logger.debug('Adding repositories %s to %s', arg, _repositories)
        _repositories.update(arg)
    _logger.debug('Adding repositories %s to %s', kwargs, _repositories)
    _repositories.update(kwargs)

def add_endpoints(*endpoints):
    global _endpoints
    _logger.debug('Adding endpoints %s to %s', endpoints, _endpoints)
    _endpoints.extend(endpoints)
