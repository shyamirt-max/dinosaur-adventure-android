from pythonforandroid.recipe import PythonRecipe


class PygameCERecipe(PythonRecipe):
    version = "2.5.8"
    url = "https://github.com/pygame-community/pygame-ce/archive/refs/tags/{version}.tar.gz"

    name = "pygame-ce"
    site_packages_name = "pygame"

    depends = [
        "python3",
        "sdl2",
        "sdl2_image",
        "sdl2_mixer",
        "sdl2_ttf",
        "setuptools",
        "jpeg",
        "png",
    ]

    call_hostpython_via_targetpython = False
    install_in_hostpython = False


recipe = PygameCERecipe()
