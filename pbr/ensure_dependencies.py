#!/usr/bin/env python3

# We want to use packages that don't come with blender by default
# To do this we need to make sure we have pip and can install the packages
try:
    from pip._internal import main as pip
except:
    import os
    import urllib.request
    import sys

    # Get the get-pip.py install file
    print('Pip is not installed, installing it now, restart the script after this is done')
    try:
        urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', 'get_pip.py')  
    except:
        if not os.path.isfile('get_pip.py'):
            print("We were unable to download https://bootstrap.pypa.io/get-pip.py")
            print("Download it manually and put at {}".format(os.path.join(os.path.dirname(__file__), 'get_pip.py')))

    # We need to clobber sys.argv so we don't confuse get-pip.py
    sys.argv = []
    import get_pip
    get_pip.main()
    exit(0)

# We have pip, install the dependencies
try:
    import cv2
except:
    pip(['install', '--no-deps', 'opencv-contrib-python'])