# -*- coding: utf-8 -*-
import os
from setuptools import find_packages, setup
import sys
import io

PY2 = sys.version_info[0] == 2

with io.open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), encoding='utf-8') as f:
    requires = f.readlines()
    if PY2:
        requires += ['futures==3.2.0', 'monotonic==1.5']

with io.open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
    README = f.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


setup(
    name='rabbitmq-rpc',
    version='0.1.1',
    packages=find_packages(),
    include_package_data=True,
    description='A modified rabbit-rpc of https://github.com/MidTin/rabbit-rpc',
    long_description=README,
    long_description_content_type="text/markdown",
    author='leo',
    author_email='liupgd@foxmail.com',
    url='https://github.com/liupgd/rabbitmq_rpc',
    license='MIT',
    install_requires=requires,
    platforms = 'any',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    entry_points={
        'console_scripts': [
            'rabbitmq_rpc=rabbitmq_rpc:main',
        ]
    }
)
