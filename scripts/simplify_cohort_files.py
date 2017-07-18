import tables
import sys

def main(filename):
    '''
    Be sure to back up your datafile before running this script!  While this
    does not delete any nodes, it does modify the file. 

    This takes the pathname

        /Cohort_0/animals/Animal_0/experiments/SomeExperiment_2011_01_01_01_01_00

    And makes it accessible as a symbolic link (i.e. shortcut) in the format

        /left_f/session_000

    Note that the data will be accessible under both the long, complicated
    pathname as well as the shorter pathname.
    '''
    with tables.openFile(filename, 'a') as fh:
        for animal in fh.root.Cohort_0.animals:
            # Create a name for the node.  If someone has two animals in the
            # cohort with the same marker and sex, then they are in trouble.
            marker = animal._v_attrs['identifier']
            sex = animal._v_attrs['sex']
            group_name = '{}_{}'.format(marker.lower(), sex.lower())

            # Check to see if the containers for the softlinks exist.  If so,
            # remove them so we can recreate them.
            if group_name in fh.root:
                fh.root._f_getChild(group_name)._f_remove(recursive=True)

            # anode is our group (e.g. /left_f) under which we will store the
            # symbolic links to the experiments (e.g. session_000)
            anode = fh.createGroup('/', group_name)

            # Load the experiment nodes, get the date portion of the name (since
            # this is in YYYY_MM_DD_HH_MM_SS format, sorting by the date portion
            # of the string will order them appropriately in chronological
            # order).
            experiments = [(e._v_name[-19:], e) for e in animal.experiments]

            # Experiment is a list of (date_string, experiment_node) tuples.
            # The sort is done on the first item in each tuple (in this case,
            # the date string).
            experiments.sort()

            # Because '0' ... '9' are < 'l', the node called 'last_paradigm'
            # will always be last in the sorted list.  Check to see if the node
            # exists.  If so, remove it (list.pop() removes the last element in
            # the list).
            if experiments[-1][0] == 'last_paradigm':
                experiments.pop()

            # Create soft links in the format /marker_sex/session_XXX that
            # points to enode (i.e. the experiment node).  For example,
            # /left_f/session_001.  This cannot deal with more than 999
            # experiments (but that would require running the animal every day
            # for almost 3 years to reach that limit).
            for i, (name, enode) in enumerate(experiments):
                fh.createSoftLink(anode, 'session_{:03}'.format(i), enode)

if __name__ == '__main__':
    for filename in sys.argv[1:]:
        main(filename)
