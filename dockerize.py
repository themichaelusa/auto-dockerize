
### STDLIB IMPORTS ###

import sys 
import glob
from distutils.dir_util import copy_tree

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
	def __init__(self, proj_name, targ_dir, lang_version, run_mod):
		self.project_name = proj_name
		self.dir_name = targ_dir.split('/')[-1]

		metadata = py_version_to_metadata[lang_version]
		extension, version, version_stdlib = metadata
		self.extension = extension
		self.version = version
		self.version_stdlib = version_stdlib

		self.filepaths = None
		self.local_paths = []
		self.local_modules = None
		self.run_path = None
		self.container_dir = None

		self.__setup_container_dir(targ_dir)
		self.__set_fpaths_localmods(run_mod)

		self.imports_and_releases = None

	def view_member_vars(self): # for testing purposes 
		print(self.__dict__)

	### SETUP ###

	def __setup_container_dir(self, targ_dir):
		# create container directory & copy target directory
		self.container_dir = self.project_name + '_autodrized'
		subprocess.run(['mkdir', self.container_dir])

		source = '{}/'.format(targ_dir)
		dest = self.container_dir + '/' + self.dir_name
		subprocess.run(['mkdir', dest])
		copy_tree(source, dest)

		#make Dockerfile binary
		dockerfile = 'Dockerfile'
		subprocess.run(['touch', dockerfile])
		subprocess.run(['mv', dockerfile, self.container_dir])

	""" Get all filepaths of target dir + set of all names of local modules.
	Also, get the path of the module that we want to run in our Dockerfile
	""" 
	def __set_fpaths_localmods(self, run_mod_name):
		container_path = self.container_dir + '/' + self.dir_name
		ext = container_path + '/**/*.{}'.format(self.extension)
		self.filepaths = glob.glob(ext, recursive=True)

		for path in self.filepaths:
			path_local = '/'.join(path.split('/')[1:])
			self.local_paths.append(path_local)

		local_modules = []
		for path in self.local_paths:
			mod = path.split('/')[-1]
			module_name = mod.split('.')[0]
			local_modules.append(module_name)

			if module_name == run_mod_name:
				self.run_path = path

		self.local_modules = set(local_modules)

	###  PRIVATE METHODS ###

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
	def __set_versions_imports(self, all_imports):
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

		self.imports_and_releases = latest_releases

	### populate Dockerfile.txt ###
	def __init_dockerfile(self):
		#open dockerfile, write neccessary dependencies
		dockerfile_loc = self.container_dir + '/Dockerfile'
		with open(dockerfile_loc, 'w') as dfile:
			curr_version = str(self.version) + '\n'
			dfile.write('FROM python:{}'.format(curr_version))

			# add files that the image uses when it builds
			for path in self.local_paths:
				dfile.write('ADD {} /\n'.format(path))

			#TODO, add require version for pip install
			for imp in self.imports_and_releases:
				dfile.write('RUN pip install {}\n'.format(imp[0]))

			# add file that is actually executed when image builds
			dfile.write('CMD [ "python3", ".{}" ]'.format(self.run_path))

	def __build_container(self):
		subprocess.run(['docker', 'build', '-t', self.proj_name, '.'])

	### PUBLIC METHODS ###

	### Create Image 
	def generate_container(self):
		imports = self.__get_all_imports()
		self.__set_versions_imports(imports)
		self.__init_dockerfile()
		#self.__build_container()

### TEST ###

""" Test command:
python3 dockerize.py test0 /Users/michaelusa/Documents/Development/Trinitum py36 test_alt
"""
if __name__ == '__main__':
	auto_dockerize = AutoDockerize(*sys.argv[1:])
	auto_dockerize.generate_container()
	#auto_dockerize.view_member_vars()
