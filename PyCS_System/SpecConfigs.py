"""

        Special Configuration file management for the PyCS system
                Written by: Eliza Diggins

"""
import os
from PyCS_Core.Configuration import read_config,_configuration_path
from PyCS_Core.Logging import set_log,log_print,make_error
import pathlib as pt
import toml
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#------------------------------------------------------ Setup ----------------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_System"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG=read_config(_configuration_path)
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#-------------------------------------------------- Sub-Functions ------------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def read_RAMSES_config(configuration_path=os.path.join(CONFIG["system"]["directories"]["bin_directory"],"configs","RAMSES_config.ini"))->dict:
    """
    Reads the specified RAMSES configuration file.
    :param configuration_path: the path in which to look for the given file.
    :return: Dictonary containing the settings
    """
    # intro debugging #
    fdbg_string = _dbg_string+"read_RAMSES_config: "
    log_print("Reading RAMSES configuration file at %s."%configuration_path,fdbg_string,"debug")

    # grabbing the data #
    try:
        RAMSES_CONFIG = toml.load(configuration_path)
        log_print("Read %s."%configuration_path,fdbg_string,"debug")
    except Exception: #TODO: This could potentially be refined for more pythonic expression
        make_error(SyntaxError,fdbg_string,"Failed to read TOML file %s."%configuration_path)

    #
    # TODO: Further alterations can be made here as necessary.
    #


    else:
        return RAMSES_CONFIG

#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#---------------------------------------------------- Functions --------------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def write_nml(nml_settings:dict,output_location:str,name=None)->None:
    """
    Write the RAMSES nml file corresponding to the input nml settings at the output location.
    :param nml_settings: The nml settings.
    :param output_location: the output location
    :param name: the name to give the file. If NONE, the standard naming convention will be used.
    :return: None
    """
    # Intro logging #
    fdbg_string = _dbg_string+"write_nml: "
    log_print("Writing nml file at %s with name %s."%(output_location,name),fdbg_string,"debug")

#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#------------------------------------------------------- Main ----------------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename,output_type="STDOUT")
    from PyCS_System.text_utils import get_options
    get_options(read_RAMSES_config(),"RAMSES Settings")
