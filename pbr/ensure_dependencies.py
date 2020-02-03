#!/usr/bin/env python3

# We want to use packages that don't come with Blender by default
# To do this we need to make sure we have pip and can install the packages


def _install_package(pkg):
    # Import/Install pip
    try:
        import pip
    except:
        # Use ensurepip module that is packaged with Blender
        import ensurepip

        ensurepip.bootstrap(upgrade=True)

        import pip

        print("[INFO] pip version {} installed".format(pip.__version__))
        print("[INFO] Please restart to use the installed pip")
        exit(0)

    # Alias pip main function for different implementations within pip versions
    pip_main = lambda x: pip.main(x) if hasattr(pip, "main") else pip._internal.main(x)

    print("[INFO] Upgrading pip version...")

    # Upgrade pip to newest version
    pip_main(
        [
            "install",
            "--trusted-host",
            "pypi.python.org",
            "--trusted-host",
            "pypi.org",
            "--trusted-host",
            "files.pythonhosted.org",
            "--upgrade",
            "pip",
        ]
    )

    print("[INFO] Installing '{}'...".format(pkg))

    # Install package
    pip_main(
        [
            "install",
            "--trusted-host",
            "pypi.python.org",
            "--trusted-host",
            "pypi.org",
            "--trusted-host",
            "files.pythonhosted.org",
            pkg,
        ]
    )


# Try to install our dependencies
try:
    import cv2
except:
    _install_package("opencv-contrib-python")
