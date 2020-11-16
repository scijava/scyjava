import setuptools
import scyjava.config
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md')) as f:
    scyjava_long_description = f.read()

setuptools.setup(
    name='scyjava',
    python_requires='>=3',
    packages=['scyjava', 'scyjava.convert'],
    py_modules=['scyjava.config'],
    version=scyjava.config.version,
    author='Philipp Hanslovsky, Curtis Rueden',
    author_email='hanslovskyp@janelia.hhmi.org',
    description='scyjava',
    long_description=scyjava_long_description,
    long_description_content_type='text/markdown',
    license='Public domain',
    url='https://github.com/scijava/scyjava',
    install_requires=['jpype1', 'jgo'],
)
