from setuptools import setup

VERSION = "0.1"

setup(
    name="plakativ",
    version=VERSION,
    author="Johannes 'josch' Schauer",
    author_email="josch@mister-muffin.de",
    description="Convert a PDF into a large poster that can be printed on multiple smaller pages.",
    long_description="file: README.md, CHANGELOG.rst",
    license="GPL-3",
    keywords="pdf poster",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Other Audience",
        "Environment :: Console",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
    ],
    url="https://gitlab.mister-muffin.de/josch/plakativ",
    download_url="https://gitlab.mister-muffin.de/josch/plakativ/repository/"
    "archive.tar.gz?ref=" + VERSION,
    test_suite="tests.test_suite",
    zip_safe=True,
    include_package_data=True,
    install_requires=["PyMuPDF"],
    entry_points={
        "setuptools.installation": ["eggsecutable = plakativ:main"],
        "console_scripts": ["plakativ = plakativ:main"],
        "gui_scripts": ["plakativ-gui = plakativ:gui"],
    },
)
