"""
        Useful utility functions for various plotting tasks throughout the system

            Written: Eliza Diggins (1/22/2023)

"""
# - Imports -#
import os
import pathlib as pt
import sys

import numpy as np
# - Imports -#
import os
import pathlib as pt
import sys

import numpy as np

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log
import matplotlib.pyplot as plt
import matplotlib as mpl
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')


#- grabbing a color dictionary -#
_available_colors = {**mpl.colors.XKCD_COLORS,**mpl.colors.BASE_COLORS,**mpl.colors.CSS4_COLORS}
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ---------------------------------------------------- Functions --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def get_color_binary_colormap(color: str) -> mpl.colors.ListedColormap:
    """
    Produces the binary colorbar corresponding the the given color
    Parameters
    ----------
    color: The color to use as the base for the map.

    Returns: The listed colormap.
    -------

    """
    # - trying the fetch the value for the underlying color -#
    if isinstance(color,str):
        # the color input was a string so we need to convert to RGBA
        try:
            color = mpl.colors.to_rgba(_available_colors[color])
        except KeyError:
            raise ValueError("The color %s was not found in the XKCD_COLORS,BASE_COLORS, or CSS4_COLORS objects of mpl.colors" % (color))
    elif isinstance(color,tuple) and len(color) == 3:
        # this is just RGB, we need to append a new value #
        color = (*color,1)
    elif isinstance(color,tuple) and len(color) == 4:
        # this is RGBA, we can pass
        pass
    else:
        raise ValueError("The color %s is not in a recognized format. Please use RGB or RGBA, or a valid string input.")

    #- manipulating the array -#
    replicated_array = np.array([color for i in range(100)]) # we replicate the array 100 times to produce the profile
    replicated_array[:,:3] = np.stack([np.linspace(0,1,100),np.linspace(0,1,100),np.linspace(0,1,100)],axis=-1)*replicated_array[:,:3]

    #- returning -#
    return mpl.colors.ListedColormap(replicated_array)




# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="STDOUT")  # send log to STDOUT.
    h = get_color_binary_colormap("orangered")
    test_array = np.random.uniform(0, 1, size=(200, 200))
    g = plt.imshow(test_array, cmap=h)
    plt.colorbar(g)
    plt.show()
