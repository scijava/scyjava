import logging
import os
import platform
import sys
import subprocess
import jpype # import module
import jpype.imports # enable java imports
from jpype.types import * # pull in types
from pathlib import Path

_logger = logging.getLogger(__name__)

# enable debug logging here if variable is set.

def _init_jvm():
    import scyjava_config2
    # jnius_config is imported here: --> jnius_config.vm_running status
    import jgo

    # sense if the vm is already running via jinus_config

    # attempt to find pyjnius.jar if the environment variable is not set
    # EE: I removed this section as it is no longer relevant with regards to 
    # JPype.

    # attempt to set JAVA_HOME if the environment variable is not set.
    # EE: This section is unchanged.

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
            if java_path.name is 'jre':
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
            
    # retrieve endpoint and repositories from scyjava_config2
    endpoints = scyjava_config2.get_endpoints()
    repositories = scyjava_config2.get_repositories()

    # use the logger to notify user that endpoints are being added
    _logger.debug('Adding jars from endpoints {0}'.format(endpoints))

    # looks like as long as there are endpoints jgo will fetch/resolve
    # the dependence and passing the classpath to jnius_config 
    # (now replaced with jpype)
    if len(endpoints) > 0:
        endpoints = endpoints[:1] + sorted(endpoints[1:])
        _logger.debug('Using endpoints %s', endpoints)
        _, workspace = jgo.resolve_dependencies(
            '+'.join(endpoints),
            m2_repo=scyjava_config2.get_m2_repo(),
            cache_dir=scyjava_config2.get_cache_dir(),
            manage_dependencies=scyjava_config2.get_manage_deps(),
            repositories=repositories,
            verbose=scyjava_config2.get_verbose()
        )
        jpype.addClassPath(os.path.join(workspace, '*'))

    # start the vm here. with jnius this is done via 'import jnius' after
    # jnius_config has been configured.
    # Initialize JPype JVM
    print('[DEBUG] Starting JPype JVM')
    jpype.startJVM()
    
    jvm_status = jpype.isJVMStarted()
    if jvm_status == True:
        print('[DEBUG] JVM status: Running')
    else:
        print('[DEBUG] JVM status: Stopped')

    # after the JPype JVM has been started, java imports can be made
    from java.lang import System
    
    # print classpath of the jvm
    #print('[DEBUG] JVM ClassPath: {0}'.format(System.getProperty("java.class.path")))