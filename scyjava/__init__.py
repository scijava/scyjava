import os
import pathlib
import subprocess
import tempfile
tmp_dir = tempfile.mkdtemp()

import jnius_config
jnius_config.add_classpath(tmp_dir)

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

from jnius import (
    autoclass as _autoclass,
    cast as _cast,
    JavaException )

from .wrap_java_class import _wrap_java_class


# for now, use grape directly:
_HashMap     = _autoclass('java.util.HashMap')
_GrapeIvy    = _autoclass('groovy.grape.GrapeIvy')
_grapeIvy    = _GrapeIvy()
_classLoader = _autoclass('groovy.lang.GroovyClassLoader')()
_Thread      = _autoclass('java.lang.Thread')
_ClassLoader = _autoclass('java.lang.ClassLoader')
get_class_loader_code="""
import java.lang.Class;
import java.lang.ClassLoader;
import java.lang.reflect.Field;

public class GetClassLoaderClass
{
  public static Class<ClassLoader> getClassLoaderClass()
  {
    return ClassLoader.class;
  }

  public static void setSystemClassLoader( ClassLoader classLoader ) throws IllegalAccessException, NoSuchFieldException
  {
    Field scl = getClassLoaderClass().getDeclaredField( "scl" );
    scl.setAccessible( true );
    scl.set( null, classLoader );
  }
}
"""
fp = pathlib.Path( tmp_dir ) / 'GetClassLoaderClass.java'
print( tmp_dir )
with open( fp, 'w' ) as f:
    f.write( get_class_loader_code )


javac = pathlib.Path( os.environ[ 'JAVA_HOME' ] ) / 'bin' / 'javac'
proc = subprocess.run(
    [ javac, '-cp', jnius_config.split_char.join( jnius_config.get_classpath() ), fp ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)
if proc.returncode != 0:
    print("Failed!")
    print ( proc.stderr )

_GetClassLoaderClass = _autoclass('GetClassLoaderClass')
_GetClassLoaderClass.setSystemClassLoader( _classLoader );
print("System classloader", _ClassLoader.getSystemClassLoader().getClass().getName())

# try:
#     _scl = _GetClassLoaderClass.getClassLoaderClass().getDeclaredField('scl')
#     print(_scl)
#     _scl.setAccessible(True)
#     _scl.set(None, _classLoader)
# except JavaException as e:
#     print(e)

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
    try:
        print("SETTING CLASSLOADER", _classLoader)
        # _Thread.currentThread().setContextClassLoader(_cast('java.lang.ClassLoader',_classLoader))
        _Thread.currentThread().setContextClassLoader(_classLoader)
    except JavaException as e:
        print( "e.classname    -- {}".format( e.classname ) )
        print( "e.innermessage -- {}".format( e.innermessage ) )
        # for st in e.stacktrace:
        #     print( st )
    # loaded_class = _classLoader.loadClass(clazz)
    # clz = Class(noinstance=True)
    # clz.instanciate_from(create_local_ref(j_env, jc))
    print("classloader", _Thread.currentThread().getContextClassLoader().getClass().getName())
    return _autoclass(clazz)
    # print( "CONSTRS ", loaded_class)
    # return _wrap_java_class(clazz, loaded_class)

def list_grapes():
    grapes = _grapeIvy.enumerateGrapes()
    grapes = {k : grapes.get(k).toString() for k in grapes.keySet().toArray()}
    return grapes


