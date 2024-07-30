from setuptools import setup, find_packages

'''
How to create distribution tar
$python setup.py sdist   -   creates a tar distribution file in ./dist/

How to install from dist tar
$python setup.py install [path to dist]

How to install from files
$python setup.py install [path to setup.py ( "." if run from CommandFramework/CommandFramework/)]

Guide
https://the-hitchhikers-guide-to-packaging.readthedocs.io/en/latest/quickstart.html
'''

# extra files (Examples) included from MANIFEST.in template
import os.path as path
pathToReadme = path.join(path.dirname(__file__), 'README.txt')
with open(pathToReadme, 'r') as f:
    long_desc = f.read()

setup(
    name='CommandFramework',
    version='1.0',
    platform='',
    description='CSU Data Acquisition Framework',
    license='Copyright 2018 Colorado State University',
    author='Aidan Duggan, Jerry Duggan',
    install_requires=['numpy', 'PyQt5','pyqtgraph', 'pytz', 'tables', 'pandas', 'serial'],
    include_package_data=True,
    package_dir={'Examples': 'Examples'},
    packages=find_packages(exclude=("Applications*", "UtilTests*")),
    long_description=long_desc
)
