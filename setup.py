#!/usr/bin/env python

from setuptools import setup, find_packages


PACKAGE = 'zc_priv_stats'

setup(
    name=PACKAGE,
    description='Calculate privacy statistics in the Zcash blockchain.',
    version='0.1',
    author='Nathan Wilcox',
    author_email='nejucomo+dev@gmail.com',
    license='GPLv3',
    url='https://github.com/nejucomo/{}'.format(PACKAGE),
    install_requires=[
        'pathlib2 >= 2.3',
        'zcli >= 0.1',
    ],

    packages=find_packages(),
    entry_points={
        'console_scripts': [
            '{} = {}.main:main'.format(
                PACKAGE.replace('_', '-'),
                PACKAGE,
            )
        ],
    }
)
