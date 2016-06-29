#!/usr/bin/env python

# -----------------------------------------------------------------------------
# Copyright (c) 2013, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from setuptools import setup
from glob import glob

__version__ = "0.1.0-dev"

classes = """
    Development Status :: 3 - Alpha
    License :: OSI Approved :: BSD License
    Topic :: Scientific/Engineering :: Bio-Informatics
    Topic :: Software Development :: Libraries :: Application Frameworks
    Topic :: Software Development :: Libraries :: Python Modules
    Programming Language :: Python
    Programming Language :: Python :: 2.7
    Programming Language :: Python :: Implementation :: CPython
    Operating System :: POSIX :: Linux
    Operating System :: MacOS :: MacOS X
"""

with open('README.rst') as f:
    long_description = f.read()

classifiers = [s.strip() for s in classes.split('\n') if s]

setup(name='qtp-biom',
      version=__version__,
      long_description=long_description,
      license="BSD",
      description='Qiita Type Plugin: BIOM',
      author="Qiita development team",
      author_email="qiita.help@gmail.com",
      url='https://github.com/qiita-spots/qtp-biom',
      test_suite='nose.collector',
      packages=['qtp_biom'],
      package_data={'qtp_biom': ['support_files/config_file.cfg']},
      scripts=glob('scripts/*'),
      extras_require={'test': ["nose >= 0.10.1", "pep8", 'httpretty']},
      install_requires=['click >= 3.3', 'biom-format >= 2.1.4, < 2.2.0',
                        'seaborn', 'qiita_client'],
      classifiers=classifiers
      )
