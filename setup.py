import setuptools
import scyjava_config

setuptools.setup(
    name='scyjava',
    python_requires='>=3',
    packages=['scyjava'],
    py_modules=['scyjava_config'],
    version=scyjava_config.version,
    author='Philipp Hanslovsky',
    author_email='hanslovskyp@janelia.hhmi.org',
    description='scyjava',
    url='https://github.com/scijava/scyjava',
    install_requires=['pyjnius', 'jgo']
    )

