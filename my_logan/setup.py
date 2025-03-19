from setuptools import setup, find_packages

def read_requirements():
    with open("requirements.txt") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("--")]

setup(
    name="my_logan",
    version="0.0.1",
    packages=find_packages(),
    install_requires=read_requirements(),  # 如果有依赖包，可以在这里列出
    author="br3ant",
    author_email="houqiqi@zepp.com",
    description="Zepp HMLogan 的封装",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)