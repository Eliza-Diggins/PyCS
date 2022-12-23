"""

System Updater
-- Last Check: 12/16 --

"""
import os
import sys
import pathlib as pt
import toml

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import utils as utils
from colorama import Fore, Style
import shutil
import tomlkit as t

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Variables ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# Setting up the debug strings #
_location = "PyCS_Core"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
fdbg_string = _dbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "UPDATE WIZARD" + Style.RESET_ALL + "]: "
# HARD CODE: the relative location of the install config file from which to generate the correct installation.
__install_config_file_path = os.path.join(str(pt.Path(os.path.realpath(__file__)).parents[0]).replace(".py", ""),
                                          "installConfigs")


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------  Sub Functions  --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def update_dict(master: dict, local: dict) -> dict:
    """
    Searches for updates to the local dictionary in master and applies them without lossing user entries in the local dict.
    :param master: The master dict from which to find updates
    :param local: The local dict with user settings.
    :return: dict.
    """
    master_keys, local_keys = master.keys(), local.keys()  # grab all of the keys

    for master_key in list(master_keys):  # cycle through each of the master keys
        if master_key not in list(local_keys):
            ### The master key isn't yet in the local keys, so we need to add it. ###
            local[master_key] = master[master_key]
        else:
            ### the master key is in the local key. We need to check if they share a setting.
            if isinstance(local[master_key], dict):
                ### resulting element is another dict, so we need to cycle again.
                local[master_key] = update_dict(master[master_key], local[master_key])
            else:
                ### the resulting element is already set so we leave it
                pass
    return local


def make_files_recur(location: str, file: dict, level=0):
    global installation_config
    if isinstance(file["files"], dict):
        ### There is still something more to do here
        for directory in file["files"]:
            # selecting each of the sub-directories
            if file["files"][directory]["setting_name"] != None:  # We have a setting for this file
                #
                # We want to check if the CONFIG already gives a path. If so, we just check that such a place exists.
                # If an alternative path doesn't exist, then we actually need to make said path.
                temp_setting_path = installation_config["system"]["directories"][
                    file["files"][directory]["setting_name"]]  # grab the path

                if temp_setting_path != "None":  # That setting has been set.
                    if os.path.exists(temp_setting_path) and os.path.isdir(temp_setting_path):
                        # We found an existing location
                        print("%s%s Found directory %s at location %s. Moving on." % (fdbg_string,
                                                                                      "\t" * level,
                                                                                      directory,
                                                                                      temp_setting_path))
                    else:
                        print(
                            "%s%sFailed to find directory at pointer in the CONFIG.ini file. Making directory %s at location %s." % (
                            fdbg_string,
                            "\t" * level,
                            directory,
                            temp_setting_path))
                        pt.Path.mkdir(pt.Path(os.path.join(temp_setting_path)),
                                      parents=True)
                else:
                    # we don't have a setting name.
                    if os.path.exists(os.path.join(location, directory)) and os.path.isdir(
                            os.path.join(location, directory)):
                        print("%s%s Found directory %s at location %s. Moving on." % (fdbg_string,
                                                                                      "\t" * level,
                                                                                      directory,
                                                                                      location))
                    else:
                        print("%s%s Making directory %s at location %s." % (fdbg_string,
                                                                            "\t" * level,
                                                                            directory,
                                                                            location))
                        pt.Path.mkdir(pt.Path(os.path.join(location, directory)),
                                      parents=True)
                    installation_config["system"]["directories"][
                        file["files"][directory]["setting_name"]] = os.path.join(location, directory)
            else:
                ### There is no setting. We just have to make it as usual.
                if os.path.exists(os.path.join(location, directory)) and os.path.isdir(
                        os.path.join(location, directory)):
                    print("%s%s Found directory %s at location %s. Moving on." % (fdbg_string,
                                                                                  "\t" * level,
                                                                                  directory,
                                                                                  location))
                else:
                    print("%s%s Making directory %s at location %s." % (fdbg_string,
                                                                        "\t" * level,
                                                                        directory,
                                                                        location))
                    pt.Path.mkdir(pt.Path(os.path.join(location, directory)),
                                  parents=True)


            if file["files"][directory]["files"] != None:
                make_files_recur(os.path.join(location,directory),file["files"][directory],level=level+1)
    else:
        ### we've run out of room.
        pass


def make_files(directory):
    global installation_config
    print("%sGenerating the file system..." % fdbg_string)
    make_files_recur(directory, install_files, level=0)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    # Startup
    ####################################################################################################################
    print("#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#")
    print("#                                                  #")
    print("#                PyCS Update Wizard                #")
    print("#            Written By: Eliza Diggins             #")
    print("#--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#")
    print("%sSearching for an installation ticket..." % fdbg_string, end=" ")

    # Locating the update ticket
    ####################################################################################################################
    if os.path.exists(os.path.join(str(pt.Path(os.path.realpath(__file__)).parents[0]).replace(".py", ""), "tkt",
                                   "ticket.INSTALL_TICKET")):
        ### The update ticket was found successfully
        print(" [" + Fore.CYAN + Style.BRIGHT + "FOUND" + Style.RESET_ALL + "]")
    else:
        print(" [" + Fore.RED + Style.BRIGHT + "FAILED" + Style.RESET_ALL + "]")
        input_tmp = input(
            "%sNo installation ticket was found. Please try reinstalling or create a ticket. Press any key to exit..." % fdbg_string)
        exit()

    #- Reading the installation ticket if it exists -#
    print("%sReading installation ticket..." % fdbg_string, end=" ")
    with open(os.path.join(str(pt.Path(os.path.realpath(__file__)).parents[0]).replace(".py", ""), "tkt",
                           "ticket.INSTALL_TICKET"), "r") as file:
        # opened the install ticket #
        __installation_directory = file.read()
        print(
            " [" + Fore.CYAN + Style.BRIGHT + "FOUND" + Style.RESET_ALL + "] Installation directory is %s." % __installation_directory)

    if not os.path.exists(__installation_directory):
        ### We can't actually find the installation directory.
        print(
            "%sChecking that the directory exists. [" % fdbg_string + Fore.RED + Style.BRIGHT + "FAILED" + Style.RESET_ALL + "]")
        input_tmp = input(
            "%sThe installation directory no longer exists. Press any key to exit..." % fdbg_string)
        exit()

    # The installation directory has been located. We now update.
    ####################################################################################################################
    os.chdir(str(pt.Path(os.path.realpath(__file__)).parents[1]))  # moving up to the git repo level

    print("%sFetching update from git." % fdbg_string)
    os.system("git fetch --all")  # Fetch all the updates.
    os.system("git reset --hard origin/master")  # Resetting the system
    print("%sUpdated the code base." % fdbg_string)

    # Managing configs
    ####################################################################################################################
    __local_configs_path = os.path.join(__installation_directory, "bin", "configs")
    local_configs = [file for file in os.listdir(__local_configs_path) if ".ini" in file]
    master_configs = [file for file in os.listdir(__install_config_file_path) if ".ini" in file]

    #- updating the configuration files -#
    print("%sFound %s local configs and %s master configs. Updating..." % (
    fdbg_string, len(local_configs), len(master_configs)))


    for master_config in master_configs:
        # We cycle through each of these looking for any issues #
        if master_config not in local_configs:
            # We don't already have this config.
            print("%sNo local version of " % fdbg_string + Fore.BLUE + str(
                master_config) + Style.RESET_ALL + " was found. Copying master copy...", end=" ")
            shutil.copy(os.path.join(__install_config_file_path, master_config),
                        os.path.join(__local_configs_path, master_config))
            print(" [" + Fore.CYAN + Style.BRIGHT + "DONE" + Style.RESET_ALL + "]")

        else:
            ### The master config matches something in local config ###
            print("%sFound both local and master versions of " % fdbg_string + Fore.BLUE + str(
                master_config) + Style.RESET_ALL + ". Resolving conflicts...", end=" ")

            # reading the master toml file
            with open(os.path.join(__install_config_file_path,master_config),"r+") as file:
                temp_config_master = t.load(file)
            with open(os.path.join(__local_configs_path,master_config),"r+") as file:
                temp_config_local = t.load(file)

            # resolved config #
            resolved_config = update_dict(temp_config_master, temp_config_local)

            #- updating the file -#
            os.remove(os.path.join(__local_configs_path, master_config))
            with open(os.path.join(__local_configs_path, master_config), "w+") as file:
                t.dump(resolved_config, file)

            print(" [" + Fore.CYAN + Style.BRIGHT + "DONE" + Style.RESET_ALL + "]")

    # --------------------------------------------------------#
    #     Finishing off with file structure                   #
    # --------------------------------------------------------#
    from PyCS_Core.Install import install_files

    installation_config = toml.load(os.path.join(__local_configs_path, "CONFIG.ini"))
    print("%sGenerating new directories of the installation." % fdbg_string, end=" ")
    make_files(__installation_directory)
    print(" [" + Fore.CYAN + Style.BRIGHT + "DONE" + Style.RESET_ALL + "]")

    os.remove(os.path.join(__local_configs_path, "CONFIG.ini"))
    with open(os.path.join(__local_configs_path, "CONFIG.ini"), "w+") as file:
        toml.dump(installation_config, file)
