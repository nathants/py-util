import setuptools


setuptools.setup(
    version="0.0.1",
    license='mit',
    name="s",
    author='nathan todd-stone',
    author_email='me@nathants.com',
    url='http://github.com/nathants/s',
    packages=setuptools.find_packages(),
    install_requires=open('requirements.txt').readlines(),
    description='[s]hared code and utilities',
)
