"""

                PyCS Installation Software for use on CHPC
                    Written by: Eliza Diggins
"""
import os
import sys
import pathlib as pt
import toml
# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import utils as utils
from colorama import Fore,Style
import shutil
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#------------------------------------------------------ Variables ------------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# Setting up the debug strings #
_location = "PyCS_Core"
_filename = pt.Path(__file__).name.replace(".py","")
_dbg_string = "%s:%s:"%(_location,_filename)
fdbg_string = _dbg_string + " ["+Fore.LIGHTGREEN_EX+Style.BRIGHT+"INSTALL WIZARD"+Style.RESET_ALL+"]: "
# HARD CODE: the relative location of the install config file from which to generate the correct installation.
__install_config_file_path=os.path.join(str(pt.Path(os.path.realpath(__file__)).parents[0]).replace(".py",""),"installConfigs")

### Generating the correct file system upon installation ###
install_files = {"files":{
    "bin": {
        "files":{
            "configs":{
                "files":None,
                "setting_name":None
            },
            "Logging":{
                "files":None,
                "setting_name":None
            }
        },
        "setting_name":"bin_directory"
    },
    "figures":{
        "files":None,
        "setting_name":"figures_directory"
    },
    "SLURM_files":{
        "files":{
            "scripts":{
                "files":None,
                "setting_name":None
            },
            "output":{
                "files":None,
                "setting_name":None
            }
        },
        "setting_name":"SLURM_directory"
    },
    "movies":{
        "files":None,
        "setting_name":"movies_directory"
    },
    "initial_conditions":{
        "files":None,
        "setting_name":"initial_conditions_directory"
    },
    "RAMSES_simulations":{
        "files":None,
        "setting_name":"RAMSES_simulations_directory"
    },
    "RAMSES_nml":{
        "files":None,
        "setting_name":"RAMSES_nml_directory"
    },
    "RAM_configs":{
        "files":None,
        "setting_name":"RAM_configs_directory"
                   }
}
}
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#---------------------------------------------------- Sub Functions ----------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def file_select():
    """
    Forces the user to select a directory.
    :return: The directory
    """
    CHECK = False
    while not CHECK:
        installation_directory = input("%s:[Input]: Please enter your desired installation directory: "%(fdbg_string))
        if os.path.exists(installation_directory) and os.path.isdir(installation_directory):
            # the path already exists
            return installation_directory
        else: # the installation directory doesn't actually exist yet.
            chk = input("%s:[%s]: The installation directory %s does not yet exist. [y] to create it. [n] to try again:"%(fdbg_string,
                                                                                                                          Fore.YELLOW+Style.BRIGHT+"WARNING"+Style.RESET_ALL,
                                                                                                                          installation_directory))
            if chk == "y":
                try:
                    pt.Path.mkdir(pt.Path(installation_directory),
                                  parents=True)
                    return installation_directory
                except Exception:
                    tmp = input("%s:[%s]: Failed to generate the installation directory %s. Press any key to try again."%(fdbg_string,
                                                                                                                          Fore.RED+Style.BRIGHT+"ERROR"+Style.RESET_ALL,
                                                                                                                          installation_directory))
            else:
                pass
        utils.clear_screen()

def make_files_recur(location:str,file:dict,level=0):
    for directory in file["files"]:
        if directory != None:
            # generate the directory
            if os.path.exists(os.path.join(location,directory)) and os.path.isdir(os.path.join(location,directory)):
                print("%s%s Found directory %s at location %s. Moving on."%(fdbg_string,
                                                                             "\t"*level,
                                                                             directory,
                                                                             location))
            else:
                print("%s%s Making directory %s at location %s." % (fdbg_string,
                                                                               "\t" * level,
                                                                               directory,
                                                                               location))
                pt.Path.mkdir(pt.Path(os.path.join(location,directory)),
                              parents=True)


            if file["files"][directory]["setting_name"] != None: # the setting name is not NONE, we need to add to config.
                installation_config["system"]["directories"][file["files"][directory]["setting_name"]] = os.path.join(location,directory)
            if file["files"][directory]["files"] != None:
                make_files_recur(os.path.join(location,directory),file["files"][directory],level=level+1)
def make_files(directory):
    print("%sGenerating the file system..."%fdbg_string)
    make_files_recur(directory,install_files,level=0)

# The File system to generate the information from.
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#------------------------------------------------------- Main ----------------------------------------------------------#
#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    print("#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#")
    print("#                                                  #")
    print("#             PyCS Installation Wizard             #")
    print("#            Written By: Eliza Diggins             #")
    print("#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#")
    #-----------------------------------------------#
    #      Grabbing the necessary system data       #
    #-----------------------------------------------#
    installation_config = toml.load(os.path.join(__install_config_file_path,"CONFIG.ini"))

    print("%sFound the installation configuration. Installing PyCS version %s."%(fdbg_string,Fore.CYAN+Style.BRIGHT+installation_config["system"]["version"]+Style.RESET_ALL))
    #--------------------------------------------------------#
    #      Getting the preferred installation location       #
    #--------------------------------------------------------#
    installation_directory = file_select()
    print("%sInstalling PyCS to directory %s."%(fdbg_string,installation_directory))
    make_files(installation_directory)
    print("%sGenerating the correct configuration files."%(fdbg_string))

    #--------------------------------------------------------#
    #              Creating the main CONFIG                  #
    #--------------------------------------------------------#
    with open(os.path.join(installation_config["system"]["directories"]["bin_directory"],"configs","CONFIG.ini"),"w") as file:
        toml.dump(installation_config,file)

    #--------------------------------------------------------#
    #            Copying other CONFIG files                  #
    #--------------------------------------------------------#
    for file in os.listdir(__install_config_file_path):
        if file != "CONFIG.ini" and file != "config.ini":
            # We actually do want to make this one.
            print("%sGenerating config file %s."%(fdbg_string,file))
            shutil.copy(os.path.join(__install_config_file_path,file),os.path.join(installation_config["system"]["directories"]["bin_directory"],"configs",file))

    #--------------------------------------------------------#
    #            Creating Install Ticket                     #
    #--------------------------------------------------------#
    if not os.path.exists(os.path.join(str(pt.Path(os.path.realpath(__file__)).parents[0]).replace(".py",""),"tkt")):
        pt.Path.mkdir(pt.Path(os.path.join(str(pt.Path(os.path.realpath(__file__)).parents[0]).replace(".py",""),"tkt")),parents=True)
    with open(os.path.join(str(pt.Path(os.path.realpath(__file__)).parents[0]).replace(".py",""),"tkt","ticket.INSTALL_TICKET"),"w+") as file:
        file.write(installation_directory)

