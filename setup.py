import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    install_req_list = fh.read().split('\n')

setuptools.setup(
    name="PM3",
    version="0.1.5",
    author="Ilario Febi",
    author_email="ilario@febi.biz",
    description="Like pm2 without node.js ;-)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ilariofebi/PM3.git ",
    # packages=setuptools.find_packages(),
    packages=['PM3', 'PM3.libs', 'PM3.model'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.9',
    install_requires=install_req_list,
    entry_points={
        "console_scripts": [
            "pm3=PM3.cli:main",
            "pm3_backend=PM3.app:main"]}
)