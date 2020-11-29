from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md')) as f:
    scyjava_long_description = f.read()

setup(
    name='scyjava',
    python_requires='>=3',
    packages=find_packages(),
    version='1.0.0',
    author='Curtis Rueden, Philipp Hanslovsky, Edward Evans',
    author_email='ctrueden@wisc.edu',
    description='scyjava',
    long_description=scyjava_long_description,
    long_description_content_type='text/markdown',
    license='Public domain',
    url='https://github.com/scijava/scyjava',
    install_requires=['jpype1', 'jgo'],
)
