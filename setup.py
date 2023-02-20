#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name="accounts",
    use_scm_version=True,
    packages=find_packages(),
    python_requires=">=3.6",
    setup_requires=["setuptools_scm"],
    install_requires=[
        "numpy",
        "scikit-learn",
        "colored",
        "curtsies",
        "python-dateutil",
    ],
    entry_points={
        "console_scripts": [
            "accounts=accounts.cli:main",
            "model=accounts.model:main",
        ],
    },
)
