#!/usr/bin/env python3

# We want to use packages that don't come with blender by default
# To do this we need to make sure we have pip and can install the packages


def _install_pip():
    import os
    import requests
    import sys

    # Get the get-pip.py install file
    print(
        "Pip is not installed, installing it now, restart the script after this is done"
    )
    try:
        r = requests.get("https://bootstrap.pypa.io/get-pip.py", stream=True)
        if r.status_code == 200:
            with open("get_pip.py", "wb") as f:
                for chunk in r:
                    f.write(chunk)
    except:
        if not os.path.isfile("get_pip.py"):
            print("We were unable to download https://bootstrap.pypa.io/get-pip.py")
            print(
                "Download it manually and put at {}".format(
                    os.path.join(os.path.dirname(__file__), "get_pip.py")
                )
            )

    # We need to clobber sys.argv so we don't confuse get-pip.py
    sys.argv = []
    import get_pip

    get_pip.main()
    exit(0)


def _install_package(args):
    try:
        import pip
        from pip._internal import main as pip_main

        pip_main(args)
    except:
        _install_pip()


# Try to install our dependencies
try:
    import cv2
except:
    _install_package(["install", "--no-deps", "opencv-contrib-python"])
