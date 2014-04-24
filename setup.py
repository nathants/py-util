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
    license='mit',
    name="shared",
    version="1",
    packages=setuptools.find_packages(),
    package_data=package_data,
    entry_points={'console_scripts': [
        'debug = s.bin.debug:main',
        'autotest = s.bin.autotest:main',
    ]},
)

setuptools.setup(**kwargs)
