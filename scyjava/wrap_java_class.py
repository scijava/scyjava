from jnius.reflect import (
    bean_getter, lower_name, Class,
    Modifier, Field, Object, Method,
    Field, Constructor, get_signature,
    JavaClass, MetaJavaClass, JavaMethod,
    JavaStaticMethod, JavaField, JavaStaticField,
    JavaMultipleMethod, find_javaclass )

def _wrap_java_class(clsname, c):
    jniname = clsname.replace('.', '/')
    clz = MetaJavaClass.get_javaclass(jniname)
    if clz:
        return clz
    classDict = {}
    constructors = []
    for constructor in c.getConstructors():
        sig = '({0})V'.format(
            ''.join([get_signature(x) for x in constructor.getParameterTypes()]))
        constructors.append((sig, constructor.isVarArgs()))
    classDict['__javaconstructor__'] = constructors

    methods = c.getMethods()
    methods_name = [x.getName() for x in methods]
    for index, method in enumerate(methods):
        name = methods_name[index]
        if name in classDict:
            continue
        count = methods_name.count(name)

        # only one method available
        if count == 1:
            static = Modifier.isStatic(method.getModifiers())
            varargs = method.isVarArgs()
            sig = '({0}){1}'.format(
                ''.join([get_signature(x) for x in method.getParameterTypes()]),
                get_signature(method.getReturnType()))
            clz = JavaStaticMethod if static else JavaMethod
            classDict[name] = clz(sig, varargs=varargs)
            if name != 'getClass' and bean_getter(name) and len(method.getParameterTypes()) == 0:
                lowername = lower_name(name[3:])
                classDict[lowername] = (lambda n: property(lambda self: getattr(self, n)()))(name)
            continue
        
        # multiple signatures
        signatures = []
        for index, subname in enumerate(methods_name):
            if subname != name:
                continue
            method = methods[index]
            sig = '({0}){1}'.format(
                ''.join([get_signature(x) for x in method.getParameterTypes()]),
                get_signature(method.getReturnType()))
            '''
            print 'm', name, sig, method.getModifiers()
            m = method.getModifiers()
            print 'Public', Modifier.isPublic(m)
            print 'Private', Modifier.isPrivate(m)
            print 'Protected', Modifier.isProtected(m)
            print 'Static', Modifier.isStatic(m)
            print 'Final', Modifier.isFinal(m)
            print 'Synchronized', Modifier.isSynchronized(m)
            print 'Volatile', Modifier.isVolatile(m)
            print 'Transient', Modifier.isTransient(m)
            print 'Native', Modifier.isNative(m)
            print 'Interface', Modifier.isInterface(m)
            print 'Abstract', Modifier.isAbstract(m)
            print 'Strict', Modifier.isStrict(m)
            '''
            signatures.append((sig, Modifier.isStatic(method.getModifiers()), method.isVarArgs()))

        classDict[name] = JavaMultipleMethod(signatures)

    def _getitem(self, index):
        try:
            return self.get(index)
        except JavaException as e:
            # initialize the subclass before getting the Class.forName
            # otherwise isInstance does not know of the subclass
            mock_exception_object = autoclass(e.classname)()
            if Class.forName("java.lang.IndexOutOfBoundsException").isInstance(mock_exception_object):
                # python for...in iteration checks for end of list by waiting for IndexError
                raise IndexError()
            else:
                raise

    for iclass in c.getInterfaces():
        if iclass.getName() == 'java.util.List':
            classDict['__getitem__'] = _getitem
            classDict['__len__'] = lambda self: self.size()
            break

    for field in c.getFields():
        static = Modifier.isStatic(field.getModifiers())
        sig = get_signature(field.getType())
        clz = JavaStaticField if static else JavaField
        classDict[field.getName()] = clz(sig)

    classDict['__javaclass__'] = clsname.replace('.', '/')
    print()
    print('classDict')
    print(classDict)
    print(clsname)
    print()

    return MetaJavaClass.__new__(
        MetaJavaClass,
        clsname,  # .replace('.', '_'),
        (JavaClass, ),
        classDict)
