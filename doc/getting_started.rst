===============
Getting Started
===============

Organization of the code
========================
The code is structured into several folders:
    cns
        This is the namespace under which much of the code I have written lives.
        To be able to use this code, you need to ensure that the parent folder
        is included in the `module search path`_.  The easiest way to do this is
        ensure that the PYTHONPATH environment variable is set to the parent
        folder.  For example, if the CNS folder lives at
        /home/brad/neurobehavior/cns, then set PYTHONPATH to
        /home/brad/neurobehavior.

        channel
            TODO
        equipment
            Collection of hardware interface modules (including TDT DSP and
            syringe pump)
        experiment
            Experiment paradigms, controllers and data storage/analysis
        signal
            Signal generation
            
    app
        This contains short scripts that are designed to load the appropriate
        modules and launch GUI experiments.
    scripts
        Typically short scripts for processing and analyzing data.  The main
        difference between scrips and apps is that scripts typically are not
        interactive.
    demo
        Demo scripts that I wrote to test the functionality of various features
        of the program.  Many of these scripts are currently broken since I
        don't maintain them well.

cns library
-----------
    experiments.data
        Objects that handle storing and analyzing experimental data.  Objects
        are typically split into RawData and AnalyzedData.
    experiments.controller
        Objects that manage the equipment equipment, responding to user input and 


.. _`module search path`: http://docs.python.org/tutorial/modules.html#the-module-search-path

The best place to start is in the demo folder.  Each script demonstrates some
aspect of the code that I have written for the behavior program.  These demos
also serve as tests: if they fail to run it means that there is a bug somewhere.

Throughout the code I adopt the idioms and patterns of the libraries that are
used.  For example, the Enthought Chaco plotting library uses the term "index"
and "value" to refer to the X and Y coordinates, respectively.  It's not clear
to me why they chose this terminology, but I adopt it for the sake of
consistency.

Dependencies
============

Windows or Mac
--------------
This code has several dependencies, most of which can be satisfied by several
prebuilt Python distributions.  Two that seem to be particularly comprehensive
are PythonXY_  and Enthought_).  Both are free for academic use.  Note that
Enthought provides a version that is compiled against the Intel MKL library
(which provides a significant speed gain for vector math and linear algebra
operations).

.. _PythonXY: http://www.pythonxy.org
.. _Enthought: http://www.enthought.com/products/epd.php

Linux or Unix
-------------
Use your package manager to install the necessary dependencies.  The Linux
repositories tend to be updated much more quickly than the repositories for
Windows and Mac, so be careful when using the latest features.  You may find
that your code will not run on Windows or Mac computers in the lab since a
binary release of the most recent version of a library is not available.
Believe me, it can be a pain to compile these libraries yourself on Windows.  I
have very little experience compiling them on a Mac, but I understand that it
can be a hassle as well.

Core (mandatory) dependencies
-----------------------------
Numpy_
    Used for numerical and vector analysis.  If you're coming from Matlab, be
    sure to check out their excellent `Numpy for Matlab Users`_ tutorial.
wxPython_ or PyQt_
    Python bindings for cross-platform GUI frameworks.  Both frameworks use
    the platform's native API, giving applications a native look-and-feel.
    Although you can use the libraries directly to generate the GUI, most of the
    code utilizes Enthought's Traits UI, which provides an abstraction layer and
    handles most of the "boilerplate" stuff.  Traits UI can utilize either
    wxPython or PyQt, so you only need one of these installed.  I generally
    prefer PyQt because it looks better out of the box.
Scipy_
    Filtering and statistical analysis.
Chaco_
    Interactive plotting.  This is what we use in our experiments.  Be sure to
    check out the examples provided with the library.
PySerial_
    Control of the New England pump.
PyTables_
    Data storage using HDF5 (hierarchial data file) format.  There is a `summary
    of HDF5 capabilities in Matlab`_.

.. _Numpy: http://numpy.scipy.org/
.. _Scipy: http://www.scipy.org/
.. _Chaco: http://code.enthought.com/projects/chaco/
.. _`Numpy for Matlab Users`: http://www.scipy.org/NumPy_for_Matlab_Users
.. _wxPython: http://www.wxpython.org/
.. _PyQt: http://www.riverbankcomputing.co.uk/software/pyqt/
.. _PySerial: http://pyserial.sourceforge.net/
.. _PyTables: http://www.pytables.org/
.. _`summary of HDF5 capabilities in Matlab`: http://www.mathworks.com/access/helpdesk/help/techdoc/ref/hdf5.html

Recommended
-----------
Matplotlib_
    Offline plotting and generating presentation quality figures (the figures
    are much nicer than what Matlab generates).
Sphinx_
    Auto-generation of HTML/PDF documentation
NumpyDoc_
    Extra modules used with Sphinx to format docstrings

.. _Matplotlib: http://matplotlib.sourceforge.net/
.. _Sphinx: http://sphinx.pocoo.org/ 
.. _NumpyDoc: http://pypi.python.org/pypi/numpydoc/

A few points for new Python programmers
=======================================
The best place to start learning Python is to download one of the distributions
(PythonXY_ or Enthought_) and work your way through the `Python tutorial`_.
Another project, `SAGE Math`_, brings together many open-source mathematical and
analytic packages (e.g. optimization, number theory, symbolic calculus, etc.)
under a Python interface; however, this project, while interesting, is primarily
oriented towards the mathematical community.  If you have only used Matlab
before, many concepts will likely be new to you (e.g.  Model-View-Controller_,
object-oriented programming, list comprehensions, namespaces).  It is crucial
that you become comfortable with these concepts before you attempt to understand
the NeuroBehavior code.

One of my favorite Python modules is IPython_, an interactive Python shell that
contains a lot of Matlab-like functionality (e.g. typing in commands one at a
time, scrolling through history, launching scripts, viewing function
documentation, etc.).  Be sure to check out the `IPython tutorial`_ for
information on how to use these features.

For editing code, the built-in IDLE_ IDE (integrated development environment) is
sufficient.  As you gain proficiency, you'll probably find another editor you
prefer better.  Options include Vim_ (my favorite, but be warned, there is a
*huge* learning curve with this program) and Eclipse_ with Pydev_ (includes the
kitchen sink).  Google "python IDE" to find the various options available.

Once you have acquired a degree of proficiency and can write a few basic Python
scripts, then you can move on to understanding how the `Enthought Traits`_
abstraction layer works.  This is a potential source of confusion since I rely
on two key types of classes: normal Python-style classes and Enthought Traited
classes.

.. _`SAGE Math`: http://www.sagemath.org/
.. _Model-View-Controller: https://svn.enthought.com/enthought/wiki/UnderstandingMVCAndTraitsUI
.. _`Python tutorial`: http://docs.python.org/tutorial/
.. _`Enthought Traits`: http://code.enthought.com/projects/traits/docs/html/traits_user_manual/index.html
.. _IPython: http://ipython.scipy.org/
.. _`IPython tutorial`: http://ipython.scipy.org/doc/manual/html/interactive/tutorial.html
.. _IDLE: http://docs.python.org/library/idle.html
.. _Eclipse: http://www.eclipse.org/
.. _Pydev: http://pydev.org/
.. _VIM: http://www.vim.org/

Normal Python style classes can be recognized because they are defined as
either: "class Equipment" or "class Equipment(object)".  A Traited class
inherits from `HasTraits`: "class Equipment(HasTraits)".  "Traited" classes are
essentially Python classes that have some additional functionality tacked on via
a third-party library (`Enthought Traits`_).  They have all the features of the
normal Python style classes that you learned about in the `Python tutorial`_.
However, one key difference is you often declare class properties in the
definition of a "Traited" class and tack on metadata about these class
properties.  This metadata is used by functions that generate the GUI for each
class.  I also wrote some functions to take advantage of the metadata available
for saving the class to a HDF5 file (see :module:`cns.data.persistence` for more
information).

Be sure to work your way through some of the examples provided in the Traits
documentation.

At some point, you're going to need to learn how to use the revision control
tools (used to track changes to the codebase and help people collaborate).
Currently we use Mercurial_.  The `master repository for NeuroBehavior`_ is
hosted at BitBucket.org_.  The time you spend learning how to use this tool will
quickly be recouped the first time you realize you've made a huge mistake and
wished you could roll back your code to a prior version or view the changes to
see if you can target the exact location where the bug was introduced).

Finally, the tools we use to maintain the documentation is Sphinx_ (which uses
`restructured text`_ for formatting).  Sphinx can generate HTML as well as
Latex_ format (this PDF was generated by having Sphinx generate the Latex source
and then using pdfTeX_ to compile it).

.. _Mercurial: http://mercurial.selenic.com/
.. _TortoiseHg: http://tortoisehg.bitbucket.org/
.. _MacHg: http://jasonfharris.com/machg
.. _Murky: http://bitbucket.org/snej/murky/wiki/
.. _BitBucket.org: http://bitbucket.org/
.. _`master repository for NeuroBehavior`: http://bitbucket.org/bburan/neurobehavior
.. _`restructured text`: http://docutils.sourceforge.net/rst.html
.. _Latex: http://www.latex-project.org/
.. _pdfTeX: http://tug.org/applications/pdftex/

.. target-notes::

Getting the NeuroBehavior code
==============================
The best way to work with a copy of the code is to install Mercurial_.  Windows
users can use TortoiseHg_, a Windows shell extension for Mercurial.  Mac users
can select from MacHg_ or Murky_ (I have no experience with these tools so you
will have to evaluate them for yourself).  If you prefer to use one of the GUI
tools, refer to their documentation for how to clone a repository.  If you are
using the shell:

>>> cd parent_directory
>>> hg clone http://bitbucket.org/bburan/neurobehavior target_folder

You now have a copy of the most up-to-date code for NeuroBehavior in the folder
parent_directory/target_folder.  To clone a specific release:

>>> hg clone http://bitbucket.org/bburan/neurobehavior#release_0.1 target_folder
