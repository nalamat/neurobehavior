The best place to start is in the demo folder.  Each script demonstrates some
aspect of the code that I have written for the behavior program.  These demos
also serve as tests: if they fail to run it means that there is a bug somewhere.

Throughout the code I adopt the idioms and patterns of the libraries that are
used.  For example, the Enthought Chaco plotting library uses the term "index"
and "value" to refer to the X and Y coordinates, respectively.  It's not clear
to me why they chose this terminology, but I adopt it for the sake of
consistency.

The best place to start is in the app folder where you will find the application launchers.  The launchers load the appropriate modules (stored in the cns folder)

I like Python XY, http://www.pythonxy.com/.  It pretty much has everything we
would need.  You may need to install a few additional libraries on top of it,
but it's usually pretty easy to do once Python XY is installed.  You can either
do the full install of Python XY or just make sure you have the following
modules:

PyQt -- GUI
Numpy --  matlab-like functionality
Scipy -- various statistical and analysis functions
Matplotlib -- plotting toolkit (matlab-like)
IPython -- interactive console
ETS -- the "traits" system I mention later in this email
PyTables -- interface to the HDF5 library for generating HDF5 files
vitables -- GUI for browsing a HDF5 file
PyVisa, PyParallel, PySerial -- for communicating with various devices via the COM or Printer port such as the Pump
MinGW -- compiler for C++ code that is sometimes included with Python modules

If you want a working version of the pump code that you can test with your new pump, let me know when it arrives.  I'll send you my latest version at that point.  I found a few bugs with the error-handling code.  The NE-1000 has some very nice error reporting capabilities (e.g. it will tell you whether a certain command is "not applicable" -- sending a "run" command while the pump is currently running returns a "not applicable" error).  Anyway, I made some fixes to the code and I'll create a version of the code that doesn't depend on any of the other modules that I've written so you can run it right away with your pump.

A potentially confusing point when looking at my code.  There are two types of "classes" that I use:
- Normal python-style classes
- "Traited" classes

Normal Python style classes can be recognized because they are defined as either: "class Equipment" or "class Equipment(object)".  A Traited class is: "class Equipment(HasTraits)".  "Traited" classes are essentially Python classes that have some additional functionality tacked on via a third-party library ("Enthought Traits").  They have all the features of the normal Python style classes that you read about.  However, the key difference is you often declare class properties in the definition of a "Traited" class and tack on metadata about these class properties.  This metadata is used by a lot of the "magic" functions that generate the GUI for each class.  I also wrote some "magic" functions to take advantage of the metadata available.  For example, we can define:

class Equipment(HasTraits):
     fs = Float(store='attribute', configurable=False, label='Sampling frequency', unit='Hz')
     attenuation = Float(store='attribute', log_changes=True, configurable=True, unit='dB')

Basically the code attaches two properties to class Equipment using Traits.  We can then "inspect" the property to find out the information we need.  The auto-generation of the GUI that allows us to configure the properties for this class would look for a "label" metadata and use that label instead of the property name if available.  This gives us a GUI:

Sampling frequency: [ enter value here ]
Attenuation: [ enter value here ]

I wrote a modified version of the GUI creation code to factor in additional metadata (specifically "configurable" and "unit").  The modified GUI creation code will create a GUI that looks like:

Sampling frequency (Hz): 100,000 Hz <= not configurable so we don't provide a field for the user to enter data
Attenuation (dB): [enter value here]

I also wrote a generic function to save information about the object to a HDF5 file.  It takes the object, looks for properties that have the 'store' metadata, and then saves those to the HDF5 file along with extra information that allows a second function to load the data and recreate the object in it's entirety.  This allows us to store our experiment data in a "Traited" class and then all we have to do is call "save_or_update_object(file_reference, data_object)" and everything is saved into a HDF5 file.  If we want to recover the data object for further analysis in Python, all we would have to do is call "load_object(file_reference, object_name)". 

I hope this helps illustrate why I decided to incorporate the added functionality of the Enthought Traits library.  The user manual for the library is here: http://code.enthought.com/projects/traits/docs/html/traits_user_manual/index.html

