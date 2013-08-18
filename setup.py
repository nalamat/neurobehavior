from distutils.core import setup
import os.path 
import glob

description = '''Module for running behavior experiments'''

base_directory = os.path.dirname(__file__)
scripts = glob.glob(os.path.join(base_directory, 'scripts', '*.py'))

setup(
    name='Neurobehavior',
    version='0.71',
    author='Brad Buran',
    author_email='bburan@alum.mit.edu',
    packages=['experiments', 'cns', 'paradigms'],
    url='http://bradburan.com/programs-and-scripts',
    license='LICENSE.txt',
    description=description,
    package_data={'experiments': ['components/*.rcx']},
    requires=['tdtpy', 'new_era'],
    scripts=scripts,
)
