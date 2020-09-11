import logging
import os
import platform
import sys
import subprocess
import jgo
import jpype
import jpype.imports
import scyjava_config

from pathlib import Path

# setup logger
_logger = logging.getLogger(__name__)

# TODO: Pass options
def start_JVM():

    # if jvm JVM is already running -- break
    if JVM_status() == True:
        print('[DEBUG]: The JVM is already running.') 
        return

    # attempt to set JAVA_HOME if the environment variable is not set.
    JAVA_HOME_STR = 'JAVA_HOME'
    if JAVA_HOME_STR not in globals():
        JAVA_HOME = None
        try:
            _logger.debug('Checking %s environment variable', JAVA_HOME_STR)
            JAVA_HOME = os.environ[JAVA_HOME_STR]
        except KeyError:
            _logger.debug('No %s environment variable', JAVA_HOME_STR)
        if not JAVA_HOME:
            # NB: This logic handles both None and empty string cases.
            _logger.debug('%s still unknown; checking with Maven', JAVA_HOME_STR)
            # attempt to find Java by interrogating maven
            # (which we have because it is needed by jgo)
            try: 
                if (platform.system() == 'Windows'):
                    mvn = str(subprocess.check_output(['mvn.cmd', '-v']))
                    mvn = mvn.replace('\\r\\n', '\\n') # Fix Windows line breaks.
                else:
                    mvn = str(subprocess.check_output(['mvn', '-v']))
            except subprocess.CalledProcessError as e:
                _logger.error('Unable to import scyjava, could not find Maven')
                return None
            _logger.debug('Maven said: %s', mvn)
            try:
                begin = mvn.index('Java home: ')
            except ValueError as e:
                # in some versions of maven it is instead called runtime
                try:
                    begin = mvn.index('runtime: ')
                except ValueError as e:
                    _logger.error('Unable to import scyjava, could not locate jre')
                    return None
            # cut out 'Java home' or 'runtime'
            begin = mvn.index(':', begin) + 2
            end = mvn.index('\\n', begin)
            JAVA_HOME = mvn[begin:end]
        java_path = Path(JAVA_HOME)
        if java_path.is_dir():
            _logger.debug('%s found at "%s"', JAVA_HOME_STR, JAVA_HOME)
            if java_path.name == 'jre':
                _logger.debug('JAVA_HOME points at jre folder; using parent instead')
                JAVA_HOME = str(java_path.parent)
            os.environ['JAVA_HOME'] = JAVA_HOME
        else:
            _logger.error('Unable to import scyjava: jre not found')
            return None
    else:
        _logger.debug('%s found in globals', JAVA_HOME_STR)

    # On Windows, add server subfolder to the PATH so jvm.dll can be found.
    if (platform.system() == 'Windows'):
        # Java 9 and later
        jvm_server_dir = os.path.join(os.environ['JAVA_HOME'], 'bin', 'server')
        if Path(os.path.join(jvm_server_dir, 'jvm.dll')).is_file():
            os.environ['PATH'] += ';' + jvm_server_dir
        else:
            # Java 8 and earlier
            jvm_server_dir = os.path.join(os.environ['JAVA_HOME'], 'jre', 'bin', 'server')
            if Path(os.path.join(jvm_server_dir, 'jvm.dll')).is_file():
                os.environ['PATH'] += ';' + jvm_server_dir
            
    # retrieve endpoint and repositories from scyjava_config
    endpoints = scyjava_config.get_endpoints()
    repositories = scyjava_config.get_repositories()

    # use the logger to notify user that endpoints are being added
    _logger.debug('Adding jars from endpoints {0}'.format(endpoints))

    # get endpoints and add to JPype class path
    if len(endpoints) > 0:
        endpoints = endpoints[:1] + sorted(endpoints[1:])
        _logger.debug('Using endpoints %s', endpoints)
        _, workspace = jgo.resolve_dependencies(
            '+'.join(endpoints),
            m2_repo=scyjava_config.get_m2_repo(),
            cache_dir=scyjava_config.get_cache_dir(),
            manage_dependencies=scyjava_config.get_manage_deps(),
            repositories=repositories,
            verbose=scyjava_config.get_verbose()
        )
        jpype.addClassPath(os.path.join(workspace, '*'))
        
    # Initialize JPype JVM
    print('[DEBUG] Starting JPype JVM')
    jpype.startJVM()

    if JVM_status() == True:
        print('[DEBUG] JVM status: Started sucessfully.')

    return

def JVM_status():
    return jpype.isJVMStarted()