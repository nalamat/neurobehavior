import os, glob, sys

def fileList(folder, match = '*.*'):
	"returns a list of all files in the given folder with the given match ('*.*' gives all files)"
	files = []
	for folder in glob.glob(folder):
		#print "folder: " + str(folder)
		# select the type of file, for instance *.jpg or all files *.*
		if folder[-1] != os.sep: folder += os.sep
		for tempfile in glob.glob(folder + match):
			files.append(tempfile)
	return files

def pathSplit(path):
	"splits a file path into folder and file parts"
	pos = path.rfind(os.sep)
	if pos == -1: return path, ""
	if pos == len(path) -1: return path, ""
	return path[:pos], path[pos+1:]

def moduleNames(folder):
	"returns the names of the classes with the same name as their modules in this folder"
	folder, junk = pathSplit(folder)
	
	filesIn = fileList(folder, "*.py")
	files = []
	for tempfile in filesIn:
		curFolder, curFile = pathSplit(tempfile)
		if curFile[0] != "_":
			useName = curFile.replace(".py", "")
			files.append(useName)

	for root, dirs, fileNames in os.walk(folder):
		for dirName in dirs:
			if os.path.exists(os.path.join(root, dirName, '__init__.py')) or os.path.exists(os.path.join(root, dirName, '__init__.pyc')):
				files.append(dirName)
	return files
