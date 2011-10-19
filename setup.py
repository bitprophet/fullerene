#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='Fullerene',
    version='0.1',
    description='A Graphite dashboarding tool',
    author='Jeff Forcier',
    author_email='jeff@bitprophet.org',
    packages=find_packages(),
    #test_suite='nose.collector',
    tests_require=['nose', 'mock', 'rudolf'],
    install_requires=['requests', 'flask', 'pyyaml'],
)
