
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
	def __set_fpaths_localmods(self, exec_file_name):
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

			if module_name == exec_file_name:
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
		all_pip_dependencies = subprocess.check_output(['pip','freeze'])
		all_pip_dependencies = all_pip_dependencies.decode('utf-8').split('\n')[:-1]

		releases = []
		for dep in all_pip_dependencies:
			package, version = dep.split('==')
			if package in all_imports:
				releases.append((package, version))

		self.imports_and_releases = releases

	def __add_duct_env(self, dfile, user_meta):
		user, proj, uuid = user_meta
		dfile.write('ENV USERNAME {}'.format(user))
		dfile.write('ENV PROJNAME {}'.format(proj))
		dfile.write('ENV UUID {}'.format(uuid))

	### populate Dockerfile.txt ###
	def __populate_dockerfile(self, user_meta=None):
		#open dockerfile, write neccessary dependencies
		dockerfile_loc = self.container_dir + '/Dockerfile'
		with open(dockerfile_loc, 'w') as dfile:
			curr_version = str(self.version)
			dfile.write('FROM python:{}\n'.format(curr_version))

			# add files that the image uses when it builds
			for path in self.local_paths:
				dfile.write('ADD {} /\n'.format(path))

			# back 
			if user_meta is not None:
				self.__add_duct_env(dfile, user_meta)

			#TODO, add require version for pip install
			for imp in self.imports_and_releases:
				dfile.write('RUN pip install {}\n'.format(imp[0]))

			# add file that is actually executed when image builds
			dfile.write('CMD [ "python3", ".{}" ]'.format(self.run_path))

	### PUBLIC METHODS ###

	### Create Image
	def generate_dockerfile(self, user_meta=None):
		imports = self.__get_all_imports()
		self.__set_versions_imports(imports)

		if user_meta is not None:
			self.__populate_dockerfile(*user_meta)
		else:
			self.__populate_dockerfile()

	def generate_compose_yaml(self):
		pass

	def build_container(self):
		print(self.project_name)
		subprocess.run(['docker', 'build', '-t', self.project_name, '.'])


### TEST ###

### test command: python3 dockerize.py test0 /Users/michaelusa/Documents/Development/Trinitum py36 test_alt
### args: project_name, project_path, python_version, exec_filename (file that's executed when container is run)
if __name__ == '__main__':
	auto_dockerize = AutoDockerize(*sys.argv[1:])
	auto_dockerize.generate_dockerfile()
	#auto_dockerize.build_container()
