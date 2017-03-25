import os
import sys
from setuptools import setup

# make sure we use qredis from the source
_this_dir = os.path.dirname(__file__)
sys.path.insert(0, _this_dir)

import qredis

requirements = [
    'redis',
    'PyQt4',
]

setup(
    name='qredis',
    version=qredis.__version__,
    description="QRedis GUI",
    author="Tiago Coutinho",
    author_email='coutinhotiago@gmail.com',
    url='https://github.com/tiagocoutinho/qredis',
    packages=['qredis', 'qredis.images', 'qredis.ui'],
    package_data={'qredis.images': ['*.png'],
                  'qredis.ui': ['*.ui'],},
    entry_points={
        'console_scripts': [
            'qredis=qredis.window:main'
        ]
    },
    install_requires=requirements,
    zip_safe=False,
    keywords='redis',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
