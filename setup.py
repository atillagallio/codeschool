# -*- coding: utf8 -*-
#
# This file were created by Python Boilerplate. Use boilerplate to start simple
# usable and best-practices compliant Python projects.
#
# Learn more about it at: http://github.com/fabiommendes/boilerplate/
#

import os
from setuptools import setup, find_packages


# Meta information
name = 'codeschool'
project = 'codeschool'
author = 'Fábio Macêdo Mendes'
version = open('VERSION').read().strip()
dirname = os.path.dirname(__file__)


# Save version and author to __meta__.py
with open(os.path.join(dirname, 'src', project, '__meta__.py'), 'w') as F:
    F.write('__version__ = %r\n__author__ = %r\n' % (version, author))


setup(
    # Basic info
    name=name,
    version=version,
    author=author,
    author_email='fabiomacedomendes@gmail.com',
    url='',
    description='An environment for teaching programming for 21st century '
                'students.',
    long_description=open('README.rst').read(),

    # Classifiers (see https://pypi.python.org/pypi?%3Aaction=list_classifiers)
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
    ],

    # Packages and depencies
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=[
        # Non-django dependencies
        'lazyutils>=0.3.1',
        'Markdown',
        'bleach',
        'PyYAML',
        'fake-factory',
        'factory-boy',
        'mommys_boy',
        'gunicorn',
        'pygments',
        'python-social-auth',
        # 'frozendict',
        # 'csscompressor',
        # 'html5lib',
        # 'slimit',
        # 'pygeneric',
        # 'pytz',

        # Django and extensions
        'django>=1.9',
        'django-model-utils',
        'django-model-reference',
        'django-picklefield',
        'django-jsonfield',
        'django-annoying',
        'django-activity-stream',
        #'django-autoslug',
        'django-compressor',
        #'django-extensions',
        #'django-guardian',
        #'django-bower',
        'django-userena',
        'django-polymorphic',
        #'django-filter',
        #'djangorestframework',
        #'jsonfield',

        # Wagtail
        'wagtail',
        'wagtail-model-tools',
        # 'wagtailfontawesome',
        # 'wagtailgmaps',
        # 'wagtailosm',

        # Jinja support
        'jinja2',
        #'django_jinja',
        'djinga',
        #'jinja2-django-tags',

        # 'ejudge', (vendorized)
        #'boxed>=0.3',
        #'psutil',
        #'pexpect',

        # CodingIo question libraries
        'markio',
        'iospec>=0.3',
        'ejudge>=0.5',
        'boxed',

        # Related libraries
        'srvice',
    ],
    extras_require={
        'dev': [
            'pytest',
            'pytest-django',
            'pytest-selenium',
            'pytest-factoryboy',
            'ipython',
        ]
    },

    # Scripts
    entry_points={
        'console_scripts': ['codeschool = codeschool.__main__:main'],
    },

    # Other configurations
    zip_safe=False,
    platforms='any',
)
