from distutils.core import setup

description = '''Module for running behavior experiments'''

setup(
    name='Neurobehavior',
    version='0.7',
    author='Brad Buran',
    author_email='bburan@alum.mit.edu',
    packages=['experiments', 'cns', 'components'],
    url='http://bradburan.com/programs-and-scripts',
    license='LICENSE.txt',
    description=description,
    #requires=['tdtpy', 'new_era'],
    scripts=['scripts/load_experiment.py', 'scripts/edit_cohort.py',
             'scripts/settings.py'], 
)

import os
import textwrap

#while True:
#    mesg = textwrap.dedent("""
#    To facilitate running the NeuroBehavior Python scripts from a Windows
#    shortcut or the command shell, we need to associate the *.py extension with
#    Python.  Note that the default Python executable is pythonw.exe, which
#    prevents a terminal window from launching when the script is invoked from a
#    shortcut or via double-clicking on the icon.
#
#    Should we setup the file association (answering yes is recommended unless
#    you're a developer and know what you're doing)? (yes/no)
#    """)
#    ans = raw_input(mesg).lower()
#    if ans == 'yes':
#        os.system('assoc .py="Python.File"')
#        os.system('ftype Python.File=pythonw.exe "%1" %#')
#        break
#    elif ans == 'no':
#        break
# 
#while True:
#    # When we first install Neurobehavior on a new computer, we need to create the
#    # appropriate folders for saving the data and related information.
#    mesg = textwrap.dedent("""
#    NeuroBehavior requires a central place to store data, logs and temporary
#    files.  Under what folder should NeuroBehavior store these files?
#    """)
#    path = os.path.abspath(raw_input(mesg))
#    correct = raw_input("Is %s the correct path? (yes/no)" % path).lower()
#    if correct == 'yes':
#        try:
#            os.makedirs(path)
#            os.makedirs(os.path.join(path, 'logs'))
#            os.makedirs(os.path.join(path, 'data'))
#            os.makedirs(os.path.join(path, 'temp'))
#            os.system('SETX /M NEUROBEHAVIOR_ROOT %s' % path)
#            break
#        except BaseException, e:
#            pass
