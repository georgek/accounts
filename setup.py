#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name="accounts",
    use_scm_version=True,
    packages=find_packages(),
    python_requires=">=3.6",
    setup_requires=["setuptools_scm"],
    install_requires=[
        "numpy~=1.13.0",
        "scikit-learn",
        "colored",
        "curtsies",
        "python-dateutil",
    ],
    scripts=[
        "scripts/convert-natwest",
        "scripts/plot",
        "accounts",
    ],
)
