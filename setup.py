import setuptools

setuptools.setup(
    name='scyjava',
    packages=['scyjava'],
    py_modules=['scyjava_config'],
    version='0.1.0-dev',
    author='Philipp Hanslovsky',
    author_email='hanslovskyp@janelia.hhmi.org',
    description='scyjava',
    url='https://github.com/scijava/scyjava',
    install_requires=['pyjnius', 'jrun']
    )

