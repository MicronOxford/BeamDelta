#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2016 David Pinto <david.pinto@bioch.ox.ac.uk>
## Copyright (C) 2019 Nicholas Hall <nicholas.hall@dtc.ox.ac.uk>
##
## Copying and distribution of this file, with or without modification,
## are permitted in any medium without royalty provided the copyright
## notice and this notice are preserved.  This file is offered as-is,
## without any warranty.

import setuptools
import setuptools.command.sdist

project_name = 'BeamDelta'
project_version = '1.2.0'

with open("README.md", "r") as fh:
    long_description = fh.read()

manifest_files = [
    "COPYING",
    "README.md",
]

class sdist(setuptools.command.sdist.sdist):
    def make_distribution(self):
        self.filelist.extend(manifest_files)
        setuptools.command.sdist.sdist.make_distribution(self)

setuptools.setup(
    name=project_name,
    version=project_version,
    author="See homepage for a complete list of contributors",
    author_email=" ",
    description="A software tool to improve microscope alignment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MicronOxford/BeamDelta",
    packages=setuptools.find_packages(),
    python_requires = '>=3.5',
    install_requires = [
        "PyQt5",
        "scikit-image",
        "scipy",
        "microscope",
    ],

    entry_points = {
        'console_scripts' : [
            'BeamDelta = BeamDelta.BeamDeltaUI:__main__',
        ]
    },

    classifiers=[
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
)
