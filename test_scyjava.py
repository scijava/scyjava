import scyjava
from jnius.reflect import Modifier
print(Modifier)

scyjava.dependency(groupId='net.imglib2', artifactId='imglib2', version='4.6.0')
# scyjava.dependency(groupId='net.imglib2', artifactId='imglib2-algorithm', version='0.5.0')
# scyjava.dependency(groupId='net.imglib2', artifactId='imglib2-realtransform')
scyjava.dependency(groupId='HTTPClient', artifactId='HTTPClient', version='0.3-3')

System = scyjava.import_class('java.lang.System')
grapes = scyjava.list_grapes()

for grape in grapes.items():
    print(grape)


ArrayList = scyjava._autoclass('java.util.ArrayList')
Interval = scyjava.import_class('net.imglib2.Interval')
print(Interval)
print(ArrayList)
