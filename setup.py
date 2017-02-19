from setuptools import setup

requirements = [
    'redis',
]

test_requirements = [
    'pytest',
    'pytest-cov',
    'pytest-faulthandler',
    'pytest-mock',
    'pytest-qt',
    'pytest-xvfb',
]

setup(
    name='qredis',
    version='0.0.1',
    description="QRedis GUI",
    author="Tiago Coutinho",
    author_email='coutinhotiago@gmail.com',
    url='https://github.com/tiagocoutinho/qredis',
    packages=['qredis', 'qredis.images',
              'qredis.tests'],
    package_data={'qredis.images': ['*.png']},
    entry_points={
        'console_scripts': [
            'qredis=qredis.window:main'
        ]
    },
    install_requires=requirements,
    zip_safe=False,
    keywords='redis',
    classifiers=[
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
