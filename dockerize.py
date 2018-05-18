import sys 
import glob
from multiprocessing.dummy import Pool
from multiprocessing import cpu_count
from constants import stdlib_py_all

import requests 
import json

def get_local_modules(all_paths):
	local = []
	for path in all_paths:
		mod = path.split('/')[-1]
		local.append(mod.split('.')[0])
	return set(local)

### Extract all names of non-local imports 
def get_all_imports(dir, ext, version):
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

### Get Release Info for all non-local imports 

def get_release_info_imports(all_imports):
	def get_wrapper(import_name):
		url = 'https://pypi.python.org/pypi/{}/json'.format(import_name)
		return (import_name, requests.get(url).json())

	pool = Pool(cpu_count())
	all_release_info = pool.map(get_wrapper, all_imports)
	pool.close()
	pool.join()

	latest_releases = []
	for r_info in all_release_info:
		import_name, info_dict = r_info
		latest_release = list(info_dict['releases'].keys())[-1]
		latest_releases.append((import_name, latest_release))

	return latest_releases

### Create Dockerfile.txt ###
#dockerfile = open('Dockerfile.txt', 'w')

### Write to Dockerfile.txt

### Create Image 

### Test Run 
if __name__ == '__main__':
	imports = get_all_imports(sys.argv[1], sys.argv[2], sys.argv[3])
	imports_release_info = get_release_info_imports(imports)
	print(imports_release_info)

