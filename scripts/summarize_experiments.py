import tables
filename = 'c:/users/brad/desktop/BNB_dt_group_5_control.cohort.hd5'

f = tables.openFile(filename, 'r')
for group in f.walkGroups():
    try:
        if group._v_attrs['klass'] == 'Animal':
            for node in f.walkNodes(group._v_pathname):
                if node._v_name == 'Data':
                    try:
                        print node.water_log[-1]['infused']
                        print node._v_attrs['duration']
                    except:
                        pass
    except:
        pass
