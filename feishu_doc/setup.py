from setuptools import setup, find_packages

setup(
    name="feishu_doc",
    version="1.0.0",
    packages=find_packages(),
    install_requires=["baseopensdk@https://lf3-static.bytednsdoc.com/obj/eden-cn/lmeh7phbozvhoz/base-open-sdk/baseopensdk-0.0.13-py3-none-any.whl"],  # 如果有依赖包，可以在这里列出
    author="br3ant",
    author_email="houqiqi@zepp.com",
    description="飞书Base Doc的封装",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/br3ant/br3ant_py_package/tree/main/feishu_doc",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)