from setuptools import find_packages, setup

setup(
    name="rmfiles",
    version="0.1.0",
    description="A utility package for creating and manipulating ReMarkable tablet files.",
    author="Jacob Oscarson",
    author_email="jacob@414soft.com",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "rmfiles=rmfiles.cli:main",
        ]
    },
    install_requires=[
        "rmscene==0.7.0",
        "numpy",
        "IPython",
        "ipdb",
        "humanize",
        "svgwrite",
    ],
)
