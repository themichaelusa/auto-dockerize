import sys 
import glob

import subprocess
from multiprocessing import Pool
from multiprocessing import cpu_count
from constants import stdlib_py_all

### Extract all filepaths of target directory
### Get set of all imports 

def get_local_modules(all_paths):
	local = []
	for path in all_paths:
		mod = path.split('/')
		mod = mod[len(mod)-1]
		local.append(mod.split('.')[0])
	return set(local)

def get_all_imports(dir, ext, version):
	#pwd = dir.split('\n')[0] #remove newline
	#pwd = str(pwd) + '/*' + '.py' # TODO: support more extensions
	#filepaths = glob.glob(pwd)

	filepaths = glob.glob(dir + '/**/*.{}'.format(ext), recursive=True)
	local_modules = get_local_modules(filepaths)

	all_imports = []
	for path in filepaths:
		lines = [line.strip('\n') for line in open(path, 'r')]
		for line in lines: 
			split = line.strip('\t').split(' ')
			if len(split) < 2:
				continue
			if (split[0] == 'import' or split[0] == 'from'):
				all_imports.append(split[1]) 

	all_imports = set([elem.strip('.') for elem in all_imports])
	return list(all_imports - stdlib_py_all[version] - local_modules)

if __name__ == '__main__':
	print(get_all_imports(sys.argv[1], sys.argv[2], sys.argv[3]))
	
### Create Dockerfile.txt ###
#dockerfile = open('Dockerfile.txt', 'w')

"""
pool = Pool(cpu_count())
### Analyze Dependencies using pipreqs 
pool.map(subprocess.run, filepaths)
pool.close()
pool.join()
"""

### Write to Dockerfile.txt

### Create Image 

### Test Run 


