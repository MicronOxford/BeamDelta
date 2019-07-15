import setuptools

project_name = 'BeamDelta'
project_version = '1.0.0+dev'

with open("README.md", "r") as fh:
    long_description = fh.read()

manifest_files = [
    "COPYING",
    "README.md",
]

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
        "sys",
        "argparse",
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