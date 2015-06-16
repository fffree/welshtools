# -*- coding: utf-8 -*-
from setuptools import setup
from welshtools import shared

def readme():
    with open("README.md") as fh:
        return fh.read()

setup(name='welshtools',
      version=shared.__version__,
      description='Utilities for working with Welsh language data',
      long_description=readme(),
      url='http://lorian.me.uk',
      author=shared.__author__,
      author_email=shared.__contact__,
      license=shared.__license__,
      packages=['welshtools'],
      scripts=['bin/welshtools'],
      #install_requires=['enchant'], #Setuptools some cannot find this pkg and
                                     #it needs to be installed manually
      zip_safe=True)
