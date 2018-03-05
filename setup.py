#!/usr/bin/env python

from distutils.core import setup, Command
import os


class TestCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        retval = os.system('python -m test')
        if retval != 0:
            raise Exception('tests failed')


setup(
    name='tornado-reverse-proxy',
    version='1.0',
    description='Simple asynchronous reverse proxy',
    url='http://blog.huangyu.me/',
    author='Yu Huang',
    author_email='diwang90@gmail.com',
    cmdclass={
        'test': TestCommand
    },
    install_requires=['tornado', 'beautifulsoup'],
    packages=['tornado_reverse_proxy'],
)
