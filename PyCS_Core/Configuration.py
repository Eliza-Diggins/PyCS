"""
        Configuration Management for PyCS Project
                Written by: Eliza Diggins
                -- Last Check: 12/16 --
"""
import os
import pathlib as pt

import toml as tml
from colorama import Fore
from matplotlib.pyplot import cm

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Variables ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
with open(os.path.join(str(pt.Path(os.path.realpath(__file__)).parents[0]).replace(".py", ""), "tkt",
                       "ticket.INSTALL_TICKET"), "r") as file:
    ### Reading the CONFIG file from the installation ticket.
    _configuration_path = os.path.join(file.read(), "bin", "configs", "CONFIG.ini")

# Setting up the debug strings #
_location = "PyCS_Core"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s" % (_location, _filename)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------------FUNCTIONS ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def read_config(configuration_path: str) -> dict:
    """
    Grabbing the configuration system from the configuration file path.
    :return: The configuration dictionary
    """
    ### reading the TOML string ###
    config_dict = tml.load(configuration_path)

    #
    #       Post Processing...
    #

    ## Manging colormaps ##
    _fdbg_string = _dbg_string + Fore.LIGHTMAGENTA_EX + ":read_config:" + Fore.WHITE
    for key in config_dict["Visualization"]["ColorMaps"]:
        try:
            config_dict["Visualization"]["ColorMaps"][key] = cm.get_cmap(config_dict["Visualization"]["ColorMaps"][key])
        except ValueError:  # The colormap doesn't exist
            raise ValueError("%s Configuration key %s failed. %s is not a colormap." % (
            _fdbg_string, key, config_dict["Visualization"]["ColorMaps"][key]))

    return config_dict


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------------  MAIN  --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    CONFIG = read_config(_configuration_path)

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------------  NOTES  -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
"""
NOTES:
"""
