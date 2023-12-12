from setuptools import setup, find_packages

setup(
    name='enhanced_lib',
    version='0.1.0',
    packages=find_packages(where='python'),
    package_dir={'': 'python'},
    url='http://your-project-url.com',
    license='Your-License',
    author='Your-Name',
    author_email='your-email@example.com',
    description='Your project description',
    install_requires=[
        # list of your project dependencies
    ],
)