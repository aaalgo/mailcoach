#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="mailcoach",
    version="0.2.0",
    packages=find_packages(),
    package_data={
        'mailcoach': ['data/*'],
    },
    install_requires=[
        "mailbox",
        "litellm"
    ],
    entry_points={
        'console_scripts': [
            'mailcoach=mailcoach.cli:main',
        ],
    },
    author="Wei Dong",
    author_email="wdong@aaalgo.com",
    description="Mailcoach",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/aaalgo/mailcoach",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
