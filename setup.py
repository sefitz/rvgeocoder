# setup.py
import os
from distutils.core import setup
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext as _build_ext

def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()

# Handling scipy dependency. See: http://stackoverflow.com/a/38276716
class build_ext(_build_ext):
    def finalize_options(self):
      _build_ext.finalize_options(self)
      # Prevent numpy from thinking it is still in its setup process:
      __builtins__.__NUMPY_SETUP__ = False
      import numpy
      self.include_dirs.append(numpy.get_include())

setup(name='rvgeocoder',
      version='1.0.8',
      author='Sefi Itzkovich',
      author_email='sefi.itzkovich@gmail.com',
      url='https://github.com/sefiit/rvgeocoder',
      packages=['rvgeocoder'],
      package_dir={'rvgeocoder': './rvgeocoder'},
      package_data={'rvgeocoder': ['rg_cities1000.csv']},
      setup_requires=['numpy>=1.16.0',],
      cmdclass={'build_ext': build_ext},
      install_requires=['numpy>=1.16.0', 'scipy>=1.3.0', 'shapely >=1.6.4.post2'],
      description='Offline reverse geocoder',
      license='lgpl',
      long_description=read('longdesc.txt'))
