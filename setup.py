import os
import setuptools


package_data = {'': ['/'.join(os.path.join(path, file).split('/')[1:])
                     for n in os.listdir('.')
                     if os.path.isdir(n)
                     and '__init__.py' in os.listdir(n)
                     for path, dirs, files in os.walk(n)
                     for file in files
                     if not any(x.startswith('.') for x in path.split('/') + [file])
                     and not file.endswith('.pyc')]}


kwargs = dict(
    version="2",
    license='mit',
    name="shared",
    author='nathan todd-stone',
    author_email='me@nathants.com',
    url='http://github.com/nathants/shared',
    packages=setuptools.find_packages(),
    package_data=package_data,
    entry_points={'console_scripts': [
        'debug = s.bin.debug:main',
        'auto-test = s.bin.auto_test:main',
        'derive-types = s.bin.derive_types:main',
    ]},
)


setuptools.setup(**kwargs)
