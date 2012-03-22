Getting Started
===============

Installing the code
-------------------

All the standard Python approaches to getting set up will work.  However, I
recommend you install this as local copy that you can edit if you wish to create
new paradigms (e.g. add the root neurobehavior folder to the PYTHONPATH
environment variable).  Right now there is a hard-coded limitation (controlled
by the function experiments.loader.get_experiment) that requires all experiment
paradigms to be inside the paradigms package.  

The approach I recommend is to use Python's pip tool.  First, let's make sure
that it's installed (PythonXY and Enthought's Python Distribution do not come
with this tool by default)::

    $ easy_install pip

Once it's installed, install a copy of Mercurial (Hg) if you haven't already.
The source code for TDTPy is managed via the Mercurial distributed version
control system and pip requires the Hg binary to checkout a copy of TDTPy::

    $ pip install mercurial

.. note::

    Installing Mercurial from source requires a working compiler.  If the above
    command fails with the error message, "unable to find vcvarsall.bat", you
    need to install a compiler.  On Windows, you can install Microsoft Visual
    Studio 2008 Express (the `version of Visual Studio`_ is important).
    Alternatively, it may be much easier to just install the TortoiseHg_
    binaries

.. _TortoiseHg: http://tortoisehg.bitbucket.org/
.. _version of Visual Studio: http://slacy.com/blog/2010/09/python-unable-to-find-vcvarsall-bat

Now, install a local (editable) copy of Neurobehavior::

    $ pip install -e hg+http://bitbucket.org/bburan/tdtpy#egg=tdt

Overriding defaults defined in cns.settings
-------------------------------------------

Many configuratble settings are defined in cns.settings.  These can be overriden
on a per-computer (or per-user account basis) by creating your own
local_settings.py file containing the values of the settings you want to
override.  Note that local_settings.py is an actual Python file, so you can
compute the values of the settings using Python expressions.

If you create a custom settings file, you need to create an environment
variable, NEUROBEHAVIOR_SETTINGS, whose value is the full path to the settings
file.  There are several ways to do this, the simplest being to open a
command-lime prompt and type::

    setx NEUROBEHAVIOR_SETTINGS c:\users\sanesadmin\user_settings.py

Note that this only sets the environment variable for the current users.  If you
wish to set the value of the variable for all users (you'll have to open the
command shell as an administrator to do so)::

    setx NEUROBEHAVIOR_SETTINGS c:\users\sanesadmin\local_settings.py /m

.. note:: 

    Technically you can call your custom settings file anything you want, but
    Antje pointed out that naming it settings.py might be confusing so it's best
    to use a different name.

