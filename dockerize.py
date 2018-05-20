
### STDLIB IMPORTS ###

import sys 
import glob

import subprocess 
from multiprocessing.dummy import Pool
from multiprocessing import cpu_count

### LOCAL IMPORTS ###

from constants import py_version_to_metadata

### EXTERNAL IMPORTS ###

import requests 
import json

### MAIN ###

class AutoDockerize:
	def __init__(self, proj_name, targ_dir, lang_version):
		self.project_name = proj_name
		self.dir = targ_dir

		metadata = py_version_to_metadata[lang_version]
		extension, version, version_stdlib = metadata
		self.extension = extension
		self.version = version
		self.version_stdlib = version_stdlib

		self.filepaths = None
		self.local_modules = None
		self.__set_fpaths_localmods()

	### SETUP && PRIVATE METHODS ###
	
	""" Get all filepaths of target dir + set of all names of local modules """ 
	def __set_fpaths_localmods(self):
		ext = self.dir + '/**/*.{}'.format(self.extension)
		self.filepaths = glob.glob(ext, recursive=True)

		local = []
		for path in self.filepaths:
			mod = path.split('/')[-1]
			local.append(mod.split('.')[0])
		self.local_modules = set(local)

	""" Extract all names of non-local imports """ 
	def __get_all_imports(self):
		all_imports = []
		for path in self.filepaths:
			lines = [line.strip('\n') for line in open(path, 'r')]
			for line in lines: 
				split = line.strip('\t').split(' ')
				if len(split) < 2:
					continue
				if (split[0] == 'import' or split[0] == 'from'):
					all_imports.append(split[1]) 

		all_imports = set([elem.strip('.') for elem in all_imports])
		return list(all_imports - self.version_stdlib - self.local_modules)

	""" Get version #'s for all non-local imports """
	def __get_versions_imports(self, all_imports):
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

	### find target script/function 

	def find_target(self):
		pass

	### Create Dockerfile.txt ###
	def __init_dockerfile(self, import_releases, run_path):
		# create new subfolder in pwd 
		dir_name = self.project_name + '_auto_drized'
		subprocess.run(['mkdir', dir_name])
		pwd = subprocess.check_output(['pwd']).decode("utf-8")
		dfile_dir = pwd + '/Dockerfile.txt'

		# create dockerfile, write releases, other stuff
		with open(dfile_dir, 'a+') as dfile:
			curr_version = version_to_num[self.version] + '\n'
			dfile.write('FROM python:{}'.format(curr_version))

			# add file 
			dfile.write('ADD {} /'.format(run_path))

			#TODO, add require version for pip install
			for imp in import_releases:
				dfile.write('RUN pip install {}'.format(imp[0]))

			dfile.write('CMD [ python3, ./{} ]'.format(run_path))

	### PUBLIC METHODS ###

	### Create Image 
	def generate_container(self, run_path):
		imports = self.__get_all_imports()
		imports_release_info = self.__get_versions_imports(imports)
		self.__init_dockerfile(imports_release_info, run_path)

### TEST ###

""" Test command:
python3 dockerize.py test0 /Users/michaelusa/Documents/Development/Trinitum py36 
"""
if __name__ == '__main__':
	print(*sys.argv[1:-1])
	auto_dockerize = AutoDockerize(*sys.argv[1:-1])
		
	action = sys.argv[-1]
	"""
	if action == 'target':
		pass
	else:
		pass
	"""

	auto_dockerize.generate_container(sys.argv[-1])
