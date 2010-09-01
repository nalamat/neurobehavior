Getting Started
===============

Organization of the code
------------------------
The code is structured into several folders:
    cns
        This is the namespace under which much of the code I have written lives.
        To be able to use this code, you need to ensure that the parent folder
        is included in the `module search path`_.  The easiest way to do this is
        ensure that the PYTHONPATH environment variable is set to the parent
        folder.  For example, if the CNS folder lives at
        /home/brad/neurobehavior/cns, then set PYTHONPATH to /home/brad/neurobehavior.
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
------------

This code has several dependencies, most of which can be satisfied by several
prebuilt Python distributions.  Two that seem to be particularly comprehensive
are PythonXY_  and Enthought_).  Both are free for academic use.

.. _PythonXY: http://www.pythonxy.org
.. _Enthought: http://www.enthought.com/products/epd.php

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
    Filtering and statistical analysis
Matplotlib_
    Offline plotting and generating presentation quality figures (the figures
    are much nicer than what Matlab generates)
Chaco_
    Interactive plotting.  This is what we use in our experiments.  Be sure to
    check out the examples provided with the library.
PySerial_
    Control of the New England pump
PyTables_
    Data storage using HDF5 (hierarchial data file) format.  There is a `summary
    of HDF5 capabilities in Matlab`_.

.. _Numpy: http://numpy.scipy.org/
.. _Scipy: http://www.scipy.org/
.. _Matplotlib: http://matplotlib.sourceforge.net/
.. _Chaco: http://code.enthought.com/projects/chaco/
.. _`Numpy for Matlab Users`: http://www.scipy.org/NumPy_for_Matlab_Users
.. _wxPython: http://www.wxpython.org/
.. _PyQt: http://www.riverbankcomputing.co.uk/software/pyqt/
.. _PySerial: http://pyserial.sourceforge.net/
.. _PyTables: http://www.pytables.org/
.. _`summary of HDF5 capabilities in Matlab`: http://www.mathworks.com/access/helpdesk/help/techdoc/ref/hdf5.html

A few points for new Python programmers
---------------------------------------

The best place to start learning Python is to download one of the distributions
(PythonXY_ or Enthought_) and work your way through the `Python tutorial`_.  If
you have only used Matlab before, many concepts will likely be new to you (e.g.
Model-View-Controller, object-oriented programming, list comprehensions,
namespaces).  It is crucial that you become comfortable with these concepts
before you attempt to understand the NeuroBehavior code.

Once you have acquired a degree of proficiency and can write a few basic Python
scripts, then you can move on to understanding how the `Enthought Traits`_
abstraction layer works.  This is a potential source of confusion since I rely
on two key types of classes: normal Python-style classes and Enthought Traited
classes.

.. _`Python tutorial`: http://docs.python.org/tutorial/
.. _`Enthought Traits`: http://code.enthought.com/projects/traits/docs/html/traits_user_manual/index.html

Normal Python style classes can be recognized because they are defined as
either: "class Equipment" or "class Equipment(object)".  A Traited class is:
"class Equipment(HasTraits)".  "Traited" classes are essentially Python classes
that have some additional functionality tacked on via a third-party library
(`Enthought Traits`_).  They have all the features of the normal Python style
classes that you learned about in the `Python tutorial`_.  However, one key
difference is you often declare class properties in the definition of a
"Traited" class and tack on metadata about these class properties.  This
metadata is used by functions that generate the GUI for each class.  I also
wrote some functions to take advantage of the metadata available for saving the
class to a HDF5 file (see `cns.data.persistence` for more information).

Be sure to work your way through some of the examples provided in the Traits
documentation.

.. target-notes::
