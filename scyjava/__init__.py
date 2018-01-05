def _get_logger(name):
    import logging
    return logging.getLogger(name)

def _init_jvm():

    import jnius_config

    import os

    CLASSPATH_STR = 'SCYJAVA_CLASSPATH'

    CLASSPATH = os.environ[CLASSPATH_STR].split(jnius_config.split_char) if CLASSPATH_STR in os.environ else []

    jnius_config.add_classpath(*CLASSPATH)

    JVM_OPTIONS_STR = 'SCYJAVA_JVM_OPTIONS'

    if JVM_OPTIONS_STR in os.environ:
        jnius_config.add_options(*os.environ[JVM_OPTIONS_STR].split(' '))

    import jnius

    scijava = None # jnius.autoclass('some scijava grab class')

    return jnius_config, jnius, scijava

logger = _get_logger('scyjava')

config, _jnius, _scijava  = _init_jvm()

from jnius import autoclass as _autoclass, cast as _cast

# for now, use grape directly:
_HashMap     = _autoclass('java.util.HashMap')
_GrapeIvy    = _autoclass('groovy.grape.GrapeIvy')
_grapeIvy    = _GrapeIvy()
_classLoader = _autoclass('groovy.lang.GroovyClassLoader')()

def _default_map(**extra_options):
    m = _HashMap()
    m.put('classLoader', _classLoader)
    m.put('autoDownload', 'true')
    m.put("noExceptions", 'false')
    for k, v in extra_options.items():
        m.put(k, v)
    return m

def repository(url, name=None, **grape_options):
    m = _default_map(**grape_options)
    m.put('name', name)
    m.put('root', url)
    return _grapeIvy.addResolver(m)

repository('http://maven.imagej.net/content/groups/public', 'imagej')


def dependency(groupId, artifactId, version=None, **grape_options):
    m = _default_map(**grape_options)
    m.put('artifactId', artifactId)
    m.put('groupId', groupId)
    m.put('version', version)
    return _grapeIvy.grab(m)

def import_class(clazz):
    return _autoclass( clazz )

def list_grapes():
    grapes = _grapeIvy.enumerateGrapes()
    grapes = {k : grapes.get(k).toString() for k in grapes.keySet().toArray()}
    return grapes


