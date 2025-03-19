from setuptools import setup, find_packages
import os


def read_requirements():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_dir, "requirements.txt")) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("--")]


setup(
    name="my_logan",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[],  # 如果有依赖包，可以在这里列出
    author="br3ant",
    author_email="houqiqi@zepp.com",
    description="Zepp HMLogan 的封装",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/br3ant/br3ant_py_package/tree/main/my_logan",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
