# -*- coding: utf8 -*-
"""
A setuptools based setup module for ocp-network-split project.

See:

* https://packaging.python.org/en/latest/distributing.html
* https://github.com/pypa/sampleproject
"""


from setuptools import setup, find_packages
import codecs
import os


setup(
    name='ocp-network-split',
    # version scheme:
    # - "x.y.1" under development, will become "x.y+1.0" when released
    # - "x.y.0" released version, there is a matching git tag
    version='0.1.0',
    description=(
        'OCP 4 platform agnostic firewall based network split tool '
        'for testing network disruptions on zone level.'),
    url='http://gitlab.com/mbukatov/ocp-network-split/',
    author='Martin Bukatovič',
    author_email='mbukatov@redhat.com',
    license='Apache License 2.0',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: System :: Networking :: Firewalls',
        'Topic :: System :: Clustering',
        'Topic :: Utilities',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.9',
        'Development Status :: 3 - Alpha',
        ],
    keywords='openshift, firewall',
    packages=find_packages(exclude=['docs', 'tests']),
    install_requires=['PyYAML'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ocp-network-split-setup=ocpnetsplit.main:main_setup',
            'ocp-network-split-sched=ocpnetsplit.main:main_sched',
            ],
        },
    # https://packaging.python.org/specifications/core-metadata/#project-url-multiple-use
    project_urls={
        # 'Documentation': 'TODO',
        # 'Bug Reports': 'TODO',
        'Source': 'https://gitlab.com/mbukatov/ocp-network-split/',
        },
    )
