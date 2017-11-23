# -*- coding: utf-8 -*-
"""Tasks for working with this project"""

from invoke import task


@task
def test(ctx):
    """Run the test suite"""
    ctx.run("pytest --color=yes --cov=owlbear --cov-report=term-missing --verbose")


@task
def run_example(ctx):
    """Start a local example server"""
    ctx.run("uvicorn example.app:app")
