import tables

fh1 = tables.openFile('parent.hd5', 'w')
fh2 = tables.openFile('child.hd5', 'w')

animalnode = fh1.createGroup('/', 'animalnode')
expnode = fh2.createGroup('/', 'experimentnode')

fh1.createExternalLink(animalnode, 'experiment_1', expnode)
