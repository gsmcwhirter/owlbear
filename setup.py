#!/usr/bin/env python

from distutils.core import setup

setup(
    name='owlbear',
    version='0.2.12',
    packages=['owlbear'],
    url="https://github.com/gsmcwhirter/owlbear",
    author="Gregory McWhirter",
    author_email="greg@ideafreemonoid.org",
    description="An app framework around uvicorn",
    install_requires=[
        'aiofiles',
    ]
)
