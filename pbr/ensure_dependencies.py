#!/usr/bin/env python3

# We want to use packages that don't come with blender by default
# To do this we need to make sure we have pip and can install the packages


def _install_pip():
    import os
    import requests
    import sys

    install_file = os.path.join(os.path.dirname(__file__), "get_pip.py")

    # Get the get-pip.py install file
    print(
        "Pip is not installed, installing it now, restart the script after this is done"
    )
    try:
        r = requests.get("https://bootstrap.pypa.io/get-pip.py", stream=True)
        if r.status_code == 200:
            with open(install_file, "wb") as f:
                for chunk in r:
                    f.write(chunk)
    except:
        if not os.path.isfile(install_file):
            print("We were unable to download https://bootstrap.pypa.io/get-pip.py")
            print(
                "Download it manually and put at {}".format(install_file)
            )

    # We need to clobber sys.argv so we don't confuse get-pip.py
    sys.argv = [""] if os.name == "nt" else []
    import get_pip

    get_pip.main()
    exit(0)


def _install_package(args):
    try:
        import pip
        import subprocess
        import sys

        subprocess.check_call([sys.executable, '-m', 'pip'] + args)
    except:
        _install_pip()


# Try to install our dependencies
try:
    import cv2
    print("cv2 found")
except:
    print("cv2 not found, installing now")
    _install_package(["install", "opencv-contrib-python"])

try:
    import PIL
    print("PIL found")
except:
    print("PIL not found, installing now")
    _install_package(["install", "Pillow"])
