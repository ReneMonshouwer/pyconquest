import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyconquest",                     # This is the name of the package
    version="0.1.3",                        # The  release version
    author="René Monshouwer",                     # Full name of the author
    author_email="rene.monshouwer@radboudumc.nl",
    description="Python code which partly mimics the conquest pacs",
    url='https://github.com/ReneMonshouwer/pyconquest',
    long_description=long_description,      # Long description read from the the readme file
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),    # List of all python modules to be installed
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],                                      # Information to filter the project on PyPi website
    python_requires='>=3.6',                # Minimum version requirement of the package
    py_modules=["pyconquest"],             # Name of the python package
    #package_dir={'':'src'},     # Directory of the source code of the package
    include_package_data = True,
    install_requires=['pydicom',
                      'pynetdicom','scikit-image']                     # Install other dependencies if any
)