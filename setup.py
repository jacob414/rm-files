from setuptools import setup, find_packages

setup(
    name='rmfiles',
    version='0.1.0',
    description='A utility package for creating and manipulating ReMarkable tablet files.',
    author='Jacob Oscarson',
    author_email='jacob@414soft.com',
    packages=find_packages(),
    install_requires=[
        'rmscene @ git+https://github.com/ricklupton/rmscene.git',
        'numpy',
        'IPython',
        'ipdb'
    ],
)
