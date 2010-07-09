from os.path import dirname, abspath, join

#BASE_PATH = 'c:/users/brad/workspace/behavior/data'
BASE_PATH = abspath(join(dirname(__file__), '../../../data'))

#ANIMAL_METADATA_FILE = 'animal_metadata.h5'
ANIMAL_IDS = ['none', 'tail', 'right', 'left', 'head', 'middle', 'red']
INVESTIGATORS = ['Brad Buran', 'Emma Sarro', 'Dan Sanes']
STUDENTS = ['Francis Manno']
ANIMAL_STATUS = ['ON WATER', 'OFF WATER']
