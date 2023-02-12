"""

        Special Configuration file management for the PyCS system
                Written by: Eliza Diggins

"""
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print, make_error
import pathlib as pt
import toml
from datetime import datetime
from PyCS_System.text_utils import get_options
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_System"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
sbatch_commands = {  # These are the batch commands that we need to be able to add to .SLURM files.
    "BATCH_TIME": "#SBATCH --time=",
    "BATCH_NODES": "#SBATCH --nodes=",
    "BATCH_STD_OUT_FRMT": "#SBATCH -o ",
    "BATCH_STD_ERR_FRMT": "#SBATCH -e ",
    "BATCH_NTASKS": "#SBATCH --ntasks=",
    "BATCH_ACCOUNT": "#SBATCH --account=",
    "BATCH_PARTITION": "#SBATCH --partition="
}


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Sub-Functions ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def tuplify_dict(dict):
    ret_dict = {}
    for key, value in dict.items():
        if isinstance(value, list):
            ret_dict[key] = tuple(value)
        else:
            ret_dict[key] = tuplify_dict(dict[key])

    return ret_dict


def find_next_available_number(list, name_format):
    check = False
    l = 1
    while not check:
        if name_format % l in list:
            l += 1
        else:
            check = True

    return name_format % l


def read_RAMSES_config(configuration_path=os.path.join(CONFIG["system"]["directories"]["bin_directory"], "configs",
                                                       "RAMSES_config.ini")) -> dict:
    """
    Reads the specified RAMSES configuration file.
    :param configuration_path: the path in which to look for the given file.
    :return: Dictonary containing the settings
    """
    # intro debugging #
    fdbg_string = _dbg_string + "read_RAMSES_config: "
    log_print("Reading RAMSES configuration file at %s." % configuration_path, fdbg_string, "debug")

    # grabbing the data #
    try:
        RAMSES_CONFIG = toml.load(configuration_path)
        log_print("Read %s." % configuration_path, fdbg_string, "debug")
    except Exception:  # TODO: This could potentially be refined for more pythonic expression
        make_error(SyntaxError, fdbg_string, "Failed to read TOML file %s." % configuration_path)

    return tuplify_dict(RAMSES_CONFIG)


def read_batch_config(configuration_path=os.path.join(CONFIG["system"]["directories"]["bin_directory"], "configs",
                                                      "batch_config.ini")) -> dict:
    """
    Reads the specified batch configuration file.
    :param configuration_path: the path in which to look for the given file.
    :return: Dictonary containing the settings
    """
    # intro debugging #
    fdbg_string = _dbg_string + "read_batch_config: "
    log_print("Reading batch configuration file at %s." % configuration_path, fdbg_string, "debug")

    # grabbing the data #
    try:
        batch_CONFIG = toml.load(configuration_path)
        log_print("Read %s." % configuration_path, fdbg_string, "debug")
    except Exception:  # TODO: This could potentially be refined for more pythonic expression
        make_error(SyntaxError, fdbg_string, "Failed to read TOML file %s." % configuration_path)

    ### Reformatting ###
    return tuplify_dict(batch_CONFIG)


def read_clustep_config(configuration_path=os.path.join(CONFIG["system"]["directories"]["bin_directory"], "configs",
                                                        "CLUSTEP_config.ini")) -> dict:
    """
    Reads the specified CLUSTEP configuration file.
    :param configuration_path: the path in which to look for the given file.
    :return: Dictonary containing the settings
    """
    # intro debugging #
    fdbg_string = _dbg_string + "read_clustep_config: "
    log_print("Reading batch configuration file at %s." % configuration_path, fdbg_string, "debug")

    # grabbing the data #
    try:
        clustep_CONFIG = toml.load(configuration_path)
        log_print("Read %s." % configuration_path, fdbg_string, "debug")
    except Exception:  # TODO: This could potentially be refined for more pythonic expression
        make_error(SyntaxError, fdbg_string, "Failed to read TOML file %s." % configuration_path)

    return tuplify_dict(clustep_CONFIG)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ---------------------------------------------------- Functions --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def write_nml(nml_settings: dict, output_location: str = CONFIG["system"]["directories"]["RAMSES_nml_directory"],
              name=None) -> str:
    """
    Write the RAMSES nml file corresponding to the input nml settings at the output location.
    :param nml_settings: The nml settings.
    :param output_location: the output location
    :param name: the name to give the file. If NONE, the standard naming convention will be used.
    :return: None
    """
    # Intro logging #
    fdbg_string = _dbg_string + "write_nml: "
    log_print("Writing nml file at %s with name %s." % (output_location, name), fdbg_string, "debug")

    # managing naming convention #
    if name == None:  # no initial name was specified to the function
        log_print("No name was given, attempting to create a name.", fdbg_string, "info")
        # grab the names of the nml files that already exist
        nml_names = [file for file in os.listdir(output_location) if ".nml" in file]
        try:
            name = nml_settings["DICE_PARAMS"]["ic_file"][0].split(".")[0][1:] + ".nml"

        except KeyError:
            name = "RAMSES_nml.nml"

        name_already_exists = name in nml_names
        l = 0
        base_name = name
        while name_already_exists:  # we need to keep fixing up the name until we find something logically reasonable.
            name = base_name.split(".")[0] + "_(%s)" % l + ".nml"
            name_already_exists = name in nml_names
            l += 1

        log_print("Found name option: %s (in %s)" % (name, output_location), fdbg_string, "info")

    # Managing CORE settings
    ####################################################################################################################

        # Manging RAYMOND / RAMSES Settings
        ################################################################################################################
    execution_mode = nml_settings["CORE"]["software"][0] # This is the execution mode we are going to be using for the simulation.
    #- Checking for a valid modality -#
    if execution_mode not in ["RAMSES","RAYMOND_A","RAYMOND_Q"]:
        make_error(ValueError,fdbg_string,"%s is not a valid execution mode. Options are RAMSES, RAYMOND_A, and RAYMOND_Q."%execution_mode)
    #- making necessary changes
    elif execution_mode == 'RAYMOND_A':
        #   RAYMOND_A has the following rules:
        #   MOND_PARAMS must be used, maxstoredcells needed
        #   DICE_Params off, filetype='gadget', init_file = path.
        #---------------------------------------------------------#
        #- Setting the correct items on and off. -#
        nml_settings["CORE"]["Enabled"]["enable_DICE_PARAMS"] = ("false","false","") # turn off dice
        nml_settings["CORE"]["Enabled"]["enable_MOND_PARAMS"] = ("true","true","") # turn on mond.

        #- Fixing the correct IC file specifications -#
        nml_settings["INIT_PARAMS"] = {} # We need to regenerate this param because its not actually in the settings.
        nml_settings["INIT_PARAMS"]["filetype"] = ("'gadget'","'gadget'","")
        nml_settings["INIT_PARAMS"]["initfile"] = nml_settings["CORE"]["ic_file"]
    elif execution_mode == "RAYMOND_Q":
        #   RAYMOND_Q has the following rules:
        #
        #
        #- Setting the correct items on and off. -#
        nml_settings["CORE"]["Enabled"]["enable_DICE_PARAMS"] = ("false","false","") # turn off dice
        nml_settings["CORE"]["Enabled"]["enable_MOND_PARAMS"] = ("true","true","") # turn on mond.
        # Removing the maxstoredcells setting #
        del nml_settings["MOND_PARAMS"]["maxstoredcells"]

        #- Fixing the correct IC file specifications -#
        nml_settings["INIT_PARAMS"] = {} # We need to regenerate this param because its not actually in the settings.
        nml_settings["INIT_PARAMS"]["filetype"] = ("'gadget'","'gadget'","")
        nml_settings["INIT_PARAMS"]["initfile"] = nml_settings["CORE"]["ic_file"]

    else:
        #   RAMSES has the following rules:
        #
        #
        # - Setting the correct items on and off. -#
        nml_settings["CORE"]["Enabled"]["enable_DICE_PARAMS"] = ("true", "true", "")  # turn on dice
        nml_settings["CORE"]["Enabled"]["enable_MOND_PARAMS"] = ("false", "false", "")  # turn off mond.

        #- Fixing the correct IC file specifications -#
        ##- grabbing necessary information -##
        ic_path = pt.Path(str(nml_settings["CORE"]["ic_file"][0])[1:-1])
        ic_dir, ic_name = str(ic_path.parents[0]),str(ic_path.name)
        nml_settings["INIT_PARAMS"] = {} # We need to regenerate this param because its not actually in the settings.
        nml_settings["INIT_PARAMS"]["filetype"] = ("'dice'","'dice'","")
        nml_settings["INIT_PARAMS"]["initfile(1)"] = ("'%s'"%ic_dir,"'%s'"%ic_dir,"")
        nml_settings["DICE_PARAMS"]["ic_file"] = ("'%s'"%ic_name,"'%s'"%ic_name,"")
    # Managing memory mode settings.
    ################################################################################################################
    mem_mode = nml_settings["CORE"]["Memory"]["mode"][0]

    ##- checking for sensibility -##
    if mem_mode not in ["tot", "max"]:
        make_error(ValueError, fdbg_string, "%s is not a reasonable memory mode. Use 'tot' or 'max'." % mem_mode)

    ##- setting correct settings - ##
    if mem_mode == "max":
        # grabbing correct values
        nml_settings["AMR_PARAMS"]["ngridmax"] = nml_settings["AMR_PARAMS"]["ngrid"]
        nml_settings["AMR_PARAMS"]["npartmax"] = nml_settings["AMR_PARAMS"]["npart"]

        # deleting
        del nml_settings["AMR_PARAMS"]["ngrid"], nml_settings["AMR_PARAMS"]["npart"]
    else:
        # grabbing correct values
        nml_settings["AMR_PARAMS"]["ngridtot"] = nml_settings["AMR_PARAMS"]["ngrid"]
        nml_settings["AMR_PARAMS"]["nparttot"] = nml_settings["AMR_PARAMS"]["npart"]

        # deleting
        del nml_settings["AMR_PARAMS"]["ngrid"], nml_settings["AMR_PARAMS"]["npart"]

    # - collecting disabled headers from [CORE.enabled] -#
    disabled_headers = [str(key).replace("enable_", "") for key, value in nml_settings["CORE"]["Enabled"].items() if
                        value[0] == "false"]

    # GENERATING THE NML FILE
    ####################################################################################################################
    if not os.path.exists(output_location):
        pt.Path(output_location).mkdir(parents=True)

    with open(os.path.join(output_location, name), "w+") as file:  # Creating the file.
        file.write("#!fortran\n")
        # Writing the nml file #
        for header in nml_settings:  # Cycle through each of the nml headers
            if header != "CORE" and header not in disabled_headers:  # we skip the "CORE" setting as its just for our usage.
                file.write("&%s\n" % header)  # Write the header

                ### Writing the sub options ###
                for option in nml_settings[header]:
                    file.write("%s=%s\n" % (option, nml_settings[header][option][0]))

                file.write("/\n\n")

    log_print("Finished writing %s in %s." % (name, output_location), fdbg_string, "info")
    return os.path.join(output_location, name)


def write_slurm_script(command_string: str,
                       save_location: str = os.path.join(CONFIG["system"]["directories"]["SLURM_directory"], "scripts"),
                       name: str = None,
                       type: str = None,
                       batch: bool = True):
    """
    Generates a .SLURM file with the given set of commands to run on the CHPC clusters. The save location is the directory
    in which to save the file. The name is the preferred name to give the file. If None, then a suitable name will be chosen.
    Alternately, if a type is specified, that will be used to create a realistic name convention.

    :param type: The type of slurm file. This will be included in the name convention.
    :param description: The description to pass to the SLURM file. These should be 1 liners.
    :param command_string: The commands to run
    :param save_location: The location in which to save the file.
    :param name: The name of the file.
    :param batch: True to pass to sbatch immediately, False to pass later.
    :return: None
    """
    ### Introduction debug ###
    datetime_string = datetime.now().strftime('%m-%d-%Y_%H-%M-%S')
    fdbg_string = _dbg_string + "write_slurm_script: "
    log_print("Writing a slurm script at %s/%s (name=%s,type=%s)." % (save_location, name, name, type), fdbg_string,
              "debug")

    ### Managing the save location ###
    if not os.path.exists(save_location):  # The save location doesn't yet exist. We will make it
        pt.Path.mkdir(pt.Path(save_location), parents=True)  # Generate the file

    ### Resolving naming issue ###
    # - Grabbing the existing files in the directory
    extant_files = [file for file in os.listdir(save_location) if
                    ".slurm" in file]  # grab all of the things in the directory
    if not name:  # There was no specified name
        if not type:  # There was also no specified type
            name = "SLURM_%s.slurm" % (datetime_string)
        else:
            # We do have a type.
            name = "SLURM_%s_%s.slurm" % (type, datetime_string)
    else:  # The name is fine.
        pass

    # - logging
    log_print("Name has been cleared. Final name is %s." % name, fdbg_string, "debug")

    ### Getting batch settings ###
    batch_default_settings = read_batch_config()  # grab the basic batch system files.
    batch_settings = get_options(batch_default_settings, "Batch Settings")  # grabbing the proper settings

    for setting in ["BATCH_STD_OUT_FRMT", "BATCH_STD_ERR_FRMT"]:
        batch_settings[setting] = tuple([os.path.join(CONFIG["system"]["directories"]["SLURM_directory"], "output",name.replace(".slurm",""),
                                                      batch_settings[setting][0])] + list(batch_settings[setting])[1:])

    #- generating the ouput if it doesn't already exist -#
    if not os.path.isdir(os.path.join(CONFIG["system"]["directories"]["SLURM_directory"], "output",name.replace(".slurm",""),
                                                      batch_settings[setting][0])):
        pt.Path.mkdir(pt.Path(os.path.join(CONFIG["system"]["directories"]["SLURM_directory"], "output",name.replace(".slurm",""))),parents=True)
    else:
        pass
    ### Writing the batch script ###
    with open(os.path.join(save_location, name), "w+") as file:  # Opening the file
        file.write("#!/bin/csh\n\n")

        for option in batch_settings:  # We cycle through the batch settings list
            file.write(sbatch_commands[option] + "%s\n" % batch_settings[option][0])

        file.write("\n\n#--- COMMANDS --- #\n")
        file.write(command_string)

    ### Batching if necessary ###
    if batch:  # we are batching
        os.system("sbatch %s" % os.path.join(save_location, name))
        os.system("squeue -u $USER")


def write_clustep_ini(dict, filename):
    """
    Writes a clustep ini from the dict in the given filename.
    """
    with open(filename, "w+") as file:
        for header in dict:
            if header != "tags":
                # These are the actually necessary options for the .ini file.
                file.write("[%s]\n" % header)
                for option in dict[header]:
                    file.write("%s=%s\n" % (option, str(dict[header][option][0])))
            else:
                # These are the "tag" options which need to be passed in the command string so we skip them.
                pass


def read_clustep_ini(file_path):
    """
    Read the Clustep parameter file at the given file_path.
    Parameters
    ----------
    file_path: the location

    Returns: dictionary with data in the parameter file
    -------

    """
    data = {}  # holds the data to return
    current_header = None  # keeps track of the current header in the toml file
    # Reading the data file
    ####################################################################################################################
    with open(file_path, "r+") as file:
        d = file.read()

    # Manipulating the data
    ####################################################################################################################
    for line in [l for l in d.split("\n") if len(l) != 0]:
        # - Removing spaces -#
        line.replace(" ", "")

        # - detecting headers -#
        if line[0] == "[":  # this is a header line
            header_string = line[1:].split("]")[0]  # grab the header name and add to data.
            data[header_string] = {}

            ##- setting the current header to know where we are -##
            current_header = header_string
        else:
            # - this is a normal line -#

            ##- Removing ; comments from the line -##
            if ";" in line:  # there is a comment that we need to remove
                line = line.split(";")[0]  # remove the comment

            # - adding the key,value combination to data -#
            key, value = line.split("=")

            ##- Trying to convert to float if possible -##
            try:
                value = float(value)
            except Exception:
                pass

            # - Storing the data in the correct place -#
            if not current_header:
                data[key] = value
            else:
                data[current_header][key] = value
    # Returning
    ####################################################################################################################
    return data


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="FILE")

    print(read_clustep_ini("/home/ediggins/PyCS/Parameter_Files/Clu_3/param_1.ini"))
