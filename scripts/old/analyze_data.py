from cns.data.h5_utils import iter_nodes

def plot_level():
    for a in cohort.animals:
        experiments = [e for e in a.experiments \ 
                       if e.paradigm.variable=='level']
        print experiments

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Data plotter')
    parser.add_argument('file', type=str, nargs=1)
    op = parser.parse_args()
    try:
        from cns.data.io import load_cohort
        cohort = load_cohort(0, op.file[0])
    except:
        from cns.data.ui import load_cohort_dialog
        cohort = load_cohort_dialog()

if __name__ == '__main__':
    main()
