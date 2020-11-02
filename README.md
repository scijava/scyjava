Supercharged Java access from Python.

Built on [JPype](https://jpype.readthedocs.io/en/latest/) and [jgo](https://github.com/scijava/jgo).

## Use Java classes from Python

```python
>>> import jpype
>>> import jpype.imports
>>> jpype.startJVM()
>>> System = jpype.JClass('java.lang.System')
>>> System.getProperty('java.version')
'1.8.0_252'
```

To pass parameters to the JVM, such as an increased max heap size:

```python
>>> import jpype
>>> import jpype.imports
>>> import scyjava.jvm
>>> scyjava.jvm.start_JVM('-Xmx6g')
>>> Runtime = jpype.JClass('java.lang.Runtime')
>>> Runtime.getRuntime().maxMemory() / 2**30
5.33349609375
```

See the [JPype documentation](https://jpype.readthedocs.io/en/latest/) for more about calling Java from Python.

## Use Maven artifacts from remote repositories

### From Maven Central

```python
>>> import sys
>>> sys.version_info
sys.version_info(major=3, minor=6, micro=5, releaselevel='final', serial=0)
>>> import scyjava_config
>>> scyjava_config.add_endpoints('org.python:jython-standalone:2.7.1')
>>> import jpype
>>> import scyjava.jvm
>>> scyjava.jvm.start_JVM()
>>> jython = jpype.JClass('org.python.util.jython')
>>> jython.main([])
Jython 2.7.1 (default:0df7adb1b397, Jun 30 2017, 19:02:43) 
[OpenJDK 64-Bit Server VM (AdoptOpenJDK)] on java1.8.0_252
Type "help", "copyright", "credits" or "license" for more information.
>>> import sys
>>> sys.version_info
sys.version_info(major=2, minor=7, micro=1, releaselevel='final', serial=0)
```

### From other Maven repositories

```python
>>> import scyjava_config
>>> scyjava_config.add_repositories({'scijava.public': 'https://maven.scijava.org/content/groups/public'})
>>> scyjava_config.add_endpoints('net.imagej:imagej:2.0.0-rc-65')
>>> import scyjava.jvm
>>> import jpype
>>> import jpype.imports
>>> from jpype import JClass, JArray, JLong
>>> scyjava.jvm.start_JVM()
>>> System = JClass('java.lang.System')
>>> System.setProperty('java.awt.headless', 'true')
>>> ImageJ = JClass('net.imagej.ImageJ')
>>> ij = ImageJ()
>>> formula = "10 * (Math.cos(0.3*p[0]) + Math.sin(0.3*p[1]))"
>>> LongArray = JArray(JLong)
>>> dims = LongArray([64, 16])
>>> blank = ij.op().getClass().getMethod('create').invoke(ij.op()).img(dims)
>>> sinusoid = ij.op().image().equation(blank, formula)
>>> print(ij.op().image().ascii(sinusoid))
,,,--+oo******oo+--,,,,,--+oo******o++--,,,,,--+oo******o++--,,,
...,--+ooo**oo++--,....,,--+ooo**oo++-,,....,,--+ooo**oo++-,,...
 ...,--++oooo++--,... ...,--++oooo++--,... ...,--++oooo++-,,...
   ..,--++++++--,..     ..,--++o+++--,..     .,,--++o+++--,..
   ..,,-++++++-,,.      ..,,-++++++-,,.      ..,--++++++-,,.
    .,,--++++--,,.       .,,--++++--,,.       .,,--++++--,..
    .,,--++++--,,.       .,,-+++++--,,.       .,,-+++++--,,.
   ..,--++++++--,..     ..,--++++++--,..     ..,--++++++-,,..
  ..,,-++oooo++-,,..   ..,,-++oooo++-,,..   ..,,-++ooo+++-,,..
...,,-++oooooo++-,,.....,,-++oooooo++-,,.....,,-++oooooo+--,,...
.,,,-++oo****oo++-,,,.,,,-++oo****oo+--,,,.,,,-++oo****oo+--,,,.
,,--++o***OO**oo++-,,,,--++o***OO**oo+--,,,,--++o***OO**oo+--,,,
---++o**OOOOOO**o++-----++o**OOOOOO*oo++-----++o**OOOOOO*oo++---
--++oo*OO####OO*oo++---++oo*OO####OO*oo++---++o**OO####OO*oo++--
+++oo*OO######O**oo+++++oo*OO######O**oo+++++oo*OO######O**oo+++
+++oo*OO######OO*oo+++++oo*OO######OO*oo+++++oo*OO######OO*oo+++
```

See the [jgo documentation](https://github.com/scijava/jgo) for more about Maven endpoints.

## Convert between Python and Java data structures

### Convert Java collections to Python

```python
>>> import jpype
>>> import jpype.imports
>>> import scyjava
>>> import scyjava.jvm
>>> scyjava.jvm.start_JVM()
>>> import scyjava.convert
>>> System = jpype.JClass('java.lang.System')
>>> props = System.getProperties()
>>> props
<java object 'java.util.Properties'>
>>> [k for k in props]
['java.runtime.name', 'sun.boot.library.path', 'java.vm.version', 'java.vm.vendor', 'java.vendor.url', 'path.separator', 'java.vm.name', 'file.encoding.pkg', 'user.country', 'sun.os.patch.level', 'java.vm.specification.name', 'user.dir', 'java.runtime.version', 'java.awt.graphicsenv', 'java.endorsed.dirs', 'os.arch', 'java.io.tmpdir', 'line.separator', 'java.vm.specification.vendor', 'os.name', 'sun.jnu.encoding', 'java.library.path', 'java.specification.name', 'java.class.version', 'sun.management.compiler', 'os.version', 'user.home', 'user.timezone', 'java.awt.printerjob', 'file.encoding', 'java.specification.version', 'java.class.path', 'user.name', 'java.vm.specification.version', 'java.home', 'sun.arch.data.model', 'user.language', 'java.specification.vendor', 'awt.toolkit', 'java.vm.info', 'java.version', 'java.ext.dirs', 'sun.boot.class.path', 'java.vendor', 'file.separator', 'java.vendor.url.bug', 'sun.io.unicode.encoding', 'sun.cpu.endian', 'sun.desktop', 'sun.cpu.isalist']
>>> [k for k in scyjava.convert.to_python(props) if k.startswith('java.vm.')]
['java.vm.version', 'java.vm.vendor', 'java.vm.name', 'java.vm.specification.name', 'java.vm.specification.vendor', 'java.vm.specification.version', 'java.vm.info']
```

### Convert Python collections to Java

```python
>>> squares = [n**2 for n in range(1, 10)]
>>> squares
[1, 4, 9, 16, 25, 36, 49, 64, 81]
>>> squares.stream()
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
AttributeError: 'list' object has no attribute 'stream'
>>> scyjava.convert.to_java(squares).stream()
<java object 'java.util.stream.ReferencePipeline.Head'>
```

### Introspect Java classes

```python
>>> NumberClass = scyjava.convert.jclass('java.lang.Number')
>>> NumberClass
<java object 'java.util.stream.ReferencePipeline.Head'>
>>> NumberClass.getName()
'java.lang.Number'
>>> NumberClass.isInstance(scyjava.convert.to_java(5))
True
>>> NumberClass.isInstance(scyjava.convert.to_java('Hello'))
False
```

## Available functions -- EE fix this

```
>>> import scyjava
>>> help(scyjava.convert)
...
FUNCTIONS
    isjava(data)
        Return whether the given data object is a Java object.

    jclass(data)
        Obtain a Java class object.

        :param data: The object from which to glean the class.
        Supported types include:
        A. Name of a class to look up, analogous to
        Class.forName("java.lang.String");
        B. A jnius.MetaJavaClass object e.g. from jnius.autoclass, analogous to
        String.class;
        C. A jnius.JavaClass object e.g. instantiated from a jnius.MetaJavaClass,
        analogous to "Hello".getClass().
        :returns: A java.lang.Class object, suitable for use with reflection.
        :raises TypeError: if the argument is not one of the aforementioned types.

    to_java(data)
        Recursively convert a Python object to a Java object.
        :param data: The Python object to convert.
        Supported types include:
        * str -> String
        * bool -> Boolean
        * int -> Integer, Long or BigInteger as appropriate
        * float -> Float, Double or BigDecimal as appropriate
        * dict -> LinkedHashMap
        * set -> LinkedHashSet
        * list -> ArrayList
        :returns: A corresponding Java object with the same contents.
        :raises TypeError: if the argument is not one of the aforementioned types.

    to_python(data)
        Recursively convert a Java object to a Python object.
        :param data: The Java object to convert.
        Supported types include:
        * String, Character -> str
        * Boolean -> bool
        * Byte, Short, Integer, Long, BigInteger -> int
        * Float, Double, BigDecimal -> float
        * Map -> collections.abc.MutableMapping (dict-like)
        * Set -> collections.abc.MutableSet (set-like)
        * List -> collections.abc.MutableSequence (list-like)
        * Collection -> collections.abc.Collection
        * Iterable -> collections.abc.Iterable
        * Iterator -> collections.abc.Iterator
        :returns: A corresponding Python object with the same contents.
        :raises TypeError: if the argument is not one of the aforementioned types.
```
