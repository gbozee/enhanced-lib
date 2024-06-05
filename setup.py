import os
from setuptools import find_packages
# from setuptools import find_packages, setup
from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize

with open('requirements.txt') as f:
    required = f.read().splitlines()


def find_cython_files(package_path):
    """Recursively finds all Cython files (`.pyx`) within a package directory."""
    pyx_files = []
    for root, _, files in os.walk(package_path):
        for f in files:
            if f.endswith(".pyx"):
                pyx_files.append(os.path.join(root, f))
    return pyx_files


extensions = cythonize(
    find_cython_files("mycythonpackage")
)  # Find all .pyx recursively


setup(
    name="enhanced_lib",
    version="0.1.16",
    packages=find_packages(),
    install_requires=required,
    ext_modules=cythonize("enhanced_lib/calculation_cy/*.pyx"),
)
