try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'A program does that is a DJ by using feedback provided by the dancers.',
    'author': 'Thomas Schaper',
    'url': 'https://gitlab.com/SilentDiscoAsAService/DJFeet',
    'download_url': 'https://gitlab.com/SilentDiscoAsAService/DJFeet',
    'author_email': 'thomas@libremail.nl',
    'version': '0.0',
    'install_requires': ['nose'],
    'packages': ['dj_feet'],
    'scripts': [],
    'entry_points': {
        'console_scripts': [
            'server = dj_feet.cli:main'
        ]
    },
    'name': 'dj_feet'
}

setup(**config)
