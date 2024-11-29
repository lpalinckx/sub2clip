from setuptools import setup

setup(
   name='sub2clip',
   version='1.0',
   description='Generate gifs from videos based on subtitles',
   packages=['subs'],  #same as name
   install_requires=[
                'PyQt5',
                'pysubs2',
                'matplotlib',
                'loguru',
                'python-ffmpeg'
    ]
)
