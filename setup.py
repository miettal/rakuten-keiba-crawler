# coding=utf-8
"""rakuten-keiba-crawlerパッケージsetupスクリプト."""

from setuptools import find_packages
from setuptools import setup


setup(
    name='rakuten-keiba-crawler',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'scrapy',
    ],
)
