import os
from setuptools import find_packages, setup

with open('requirements.txt') as f:
    required = f.read().splitlines()



setup(
    name="enhanced_lib",
    version="0.1.16",
    packages=find_packages(),
    install_requires=required,
)
