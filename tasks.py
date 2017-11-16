# -*- coding: utf-8 -*-
"""Tasks for working with this project"""

from invoke import task


@task
def test(ctx):
    ctx.run("pytest --color=yes --cov=owlbear --cov-report=term-missing --verbose")
