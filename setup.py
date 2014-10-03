import os
import setuptools


setuptools.setup(
    version="0.0.2",
    license='mit',
    name="s",
    author='nathan todd-stone',
    author_email='me@nathants.com',
    url='http://github.com/nathants/s',
    install_requires=open('requirements.txt').readlines(),
    packages=setuptools.find_packages(),
    entry_points={'console_scripts': [
        '{} = s.bin.{}:main'.format(
            x.replace('.py', '').replace('_', '-'),
            x.replace('.py', '')
        )
        for x in os.listdir('s/bin')
        if not x.startswith('_')
        and x.endswith('.py')
    ]},
)
