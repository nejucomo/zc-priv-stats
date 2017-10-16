#!/usr/bin/env python

from setuptools import setup, find_packages


PACKAGE = 'zc-priv-stats'
MODULE = PACKAGE.replace('-', '_')

setup(
    name=PACKAGE,
    description='Calculate privacy statistics in the Zcash blockchain.',
    version='0.1',
    author='Nathan Wilcox',
    author_email='nejucomo+dev@gmail.com',
    license='GPLv3',
    url='https://github.com/nejucomo/{}'.format(PACKAGE),
    install_requires=[
        'matplotlib >= 2.0.2',
        'pathlib2 >= 2.3',
        'zcli >= 0.1',
    ],

    packages=find_packages(),
    entry_points={
        'console_scripts': [
            '{} = {}.main:main'.format(PACKAGE, MODULE),
            '{}-plots = {}.plot:main'.format(PACKAGE, MODULE),
            '{}-toprec = {}.toprec:main'.format(PACKAGE, MODULE),
        ],
    }
)
