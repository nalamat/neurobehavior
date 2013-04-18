from distutils.core import setup

description = '''Module for running behavior experiments'''

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
    scripts=['scripts/load_experiment.py', 
             'scripts/edit_cohort.py',
             'scripts/review_physiology.py',
             'scripts/decimate.py',
             'scripts/process_batchfile.py',
             'scripts/strip_extra_physiology.py',
             'scripts/split_physiology_file.py',
             'scripts/plot_lfp.py',
            ]
)
