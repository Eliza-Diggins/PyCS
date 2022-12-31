"""

Grabs a report on a specified IC file.
    Written by: Eliza Diggins
"""
import sys
import pathlib as pt
import os

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from copy import deepcopy
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print, make_error
import pathlib as pt
from PyCS_System.SimulationMangement import read_ic_log
from PyCS_System.SpecConfigs import read_clustep_ini
import toml
from datetime import datetime
import pynbody as pyn
import matplotlib.pyplot as plt
import numpy as np
from PyCS_System.text_utils import file_select, print_title
from PyCS_Analysis.Images import make_plot
from PyCS_Analysis.Profiles import make_profile_plot, make_profiles_plot
from PyCS_Analysis.Analysis_Utils import split_binary_collision, find_gas_COM
from PyCS_Analysis.builtin_functions import dehnen_profile,dehnen_mass_profile
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Tools"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Static Vars -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# Profile config contains all of the profiles we generate in the process of building the report.
__profile_config = {
    "density": {
        "logx": True,
        "logy": True,
        "title": "Cluster Density",
        "units_x":"kpc"
    },
    "temp": {
        "logx": True,
        "logy": False,
        "title": "ICM Temperature",
        "family": "gas"
    },
    "mass_enc": {
        "logx": True,
        "logy": True,
        "title": "Enclosed Mass",
    },
    "dyntime": {
        "logy": False,
        "logx": True,
        "title": "Dynamical Time"
    },
    "g_spherical": {
        "logy": True,
        "logx": True,
        "title": "Spherical Potential"
    },
    "p": {
        "logy": True,
        "logx": True,
        "title": "Gas Pressure",
        "family": "gas"
    }
}
# These are additional profiles which are generated with mixed entities.
__multi_profile_config = [
    {"name": "densities",
     "kwargs": {"logx": True, "logy": True, "title": "Cluster Density Profiles"},
     "dat": [
         {"quantity": "density",
          "q_kwargs": {"family": "dm",
                       "color": "black",
                       "ls": "-",
                       "label": r"$\rho_{\mathrm{dm}}(r)$"}
          },
         {"quantity": "density",
          "q_kwargs": {"color": "blue",
                       "ls": "-",
                       "label": r"$\rho_{\mathrm{tot}}(r)$"}},
         {"quantity": "density",
          "q_kwargs": {"family": "gas",
                       "color": "red",
                       "ls": "-",
                       "label": r"$\rho_{\mathrm{gas}}(r)$"}}
     ]},
    {"name": "masses",
     "kwargs": {"logx": True, "logy": True, "title": "Cluster Mass Profiles"},
     "dat": [
         {"quantity": "mass_enc",
          "q_kwargs": {"family": "dm",
                       "color": "black",
                       "ls": "-",
                       "label": r"$M_{\mathrm{dm}}(<r)$",
                       "Lambda":lambda x: x**3}
          },
         {"quantity": "mass_enc",
          "q_kwargs": {"color": "blue",
                       "ls": "-",
                       "label": r"$M_{\mathrm{tot}}(<r)$"}},
         {"quantity": "mass_enc",
          "q_kwargs": {"family": "gas",
                       "color": "red",
                       "ls": "-",
                       "label": r"$M_{\mathrm{gas}}(<r)$"}}
     ]}
]
# Default line configurations
__line_config = {
    "lw": 2,
    "ls": "-",
    "color": "k",
    "marker": "s"
}

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ---------------------------------------------------- Functions --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def get_theoretical_lambda(qty,parameter_dict,**kwargs):
    """
    Uses the specified ``qty`` and ``parameter_dict`` to determine the correct theoretical profile to return as a
    lambda function. if ``family`` is unspecified, then we will consider all of the available families.

    Parameters
    ----------
    qty: The quantity that is being plotted.
    parameter_file: the parameter datafile dictionary to pull values from.

    Returns: a lambda function of the correct theoretical profile.
    -------

    """
    # Intro debugging
    ####################################################################################################################
    fdbg_string = "%s:get_theoretical_lambda: "%_dbg_string
    log_print("Generating %s profile for the given IC file."%qty,fdbg_string,"debug")
    # Setup
    ####################################################################################################################
    #- Coercing family kwargs into the correct form for this use -#
    family = []
    if "family" in kwargs:
        if kwargs["family"] != "gas":
            # the family is specified, but isn't gas. We expect this case to be "dm" from the __param_dicts, but we need to change it.
            family = ["dark_matter"]
        elif kwargs["family"] == "gas":
            family = ["gas"]
    else:
        family=["gas","dark_matter"]

    #- unit_fetch and coercion
    # here we control all of the parameter data in order to get the right units.
    parameter_dict["gas"]["M_gas"] = parameter_dict["gas"]["M_gas"]*(1e10)*pyn.units.Unit("Msol")
    parameter_dict["gas"]["a_gas"] = parameter_dict["gas"]["a_gas"]*(pyn.units.Unit("kpc"))
    parameter_dict["dark_matter"]["M_dm"] = parameter_dict["dark_matter"]["M_dm"]*(1e10)*pyn.units.Unit("Msol")
    parameter_dict["dark_matter"]["a_dm"] = parameter_dict["dark_matter"]["a_dm"]*(pyn.units.Unit("kpc"))

    kwgs = {}
    if "units_x" in kwargs:
        kwgs["independent_unit"] = kwargs["units_x"]
    if "units_y" in kwargs:
        kwgs["dependent_unit"] = kwargs["units_y"]
    # Generating the correct profiles
    ####################################################################################################################
    lambdas = []
    under_labels = {"gas":"gas","dark_matter":"dm"}
    #- generating the functions -#
    for fam in family: # cycle through all of the families
        if qty == "density":
            #- Managing the Dehnen profile -#
            lambdas.append(dehnen_profile(parameter_dict[fam]["M_%s"%under_labels[fam]],
                                          parameter_dict[fam]["gamma_%s"%under_labels[fam]],
                                          parameter_dict[fam]["a_%s"%under_labels[fam]],
                                          **kwgs))
        elif qty == "mass_enc":
            lambdas.append(dehnen_mass_profile(parameter_dict[fam]["M_%s"%under_labels[fam]],
                                          parameter_dict[fam]["gamma_%s"%under_labels[fam]],
                                          parameter_dict[fam]["a_%s"%under_labels[fam]],
                                          **kwgs))
        else:
            return None

    # Returning
    ####################################################################################################################
    if len(lambdas) > 1:
        return lambda r: np.sum([l(r) for l in lambdas],axis=0)
    else:
        return lambdas[0]


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ MAIN -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    # Argument Parsing
    ########################################################################################################################
    parser = argparse.ArgumentParser()  # setting up the command line argument parser
    parser.add_argument("-o", "--output_type", type=str, default="FILE", help="The type of output to use for logging.")
    parser.add_argument("-l", "--logging_level", type=int, default=10, help="The level of logging to use.")
    # parser.add_argument("-nb","--no_batch",action="store_true",help="Use batch to run.") TODO: Is this worth it for versatility?
    args = parser.parse_args()

    # Setup
    ########################################################################################################################
    # - Logging -#
    set_log(_filename, output_type=args.output_type, level=args.logging_level)

    # - Making a title -#
    print_title("Initial Conditions Reports", "Eliza Diggins")

    # - Dataset creation -#
    report_data = {"General": {}}

    # Selecting an IC file
    ####################################################################################################################
    initial_condition_file = file_select(CONFIG["system"]["directories"]["initial_conditions_directory"],
                                         conditions=lambda fn: any(i in fn for i in [".dat", ".g2", ".g1"]))

    # Reading from the IC log
    ####################################################################################################################
    iclog = read_ic_log()  # reading the IC log.

    if not initial_condition_file in iclog:  # we don't have an entry.
        make_error(ValueError, _dbg_string, "Failed to find an IC log entry for %s." % initial_condition_file)
        exit()
    else:
        log_data = iclog[initial_condition_file] # fetching iclog for the given entry.

    # Opening the IC file and grabbing preliminary data
    ####################################################################################################################
    #
    # ----> This is global data that applies to all IC files regardless of form.
    #

    log_print("Attempting to open the selected file at %s." % os.path.join(
        CONFIG["system"]["directories"]["initial_conditions_directory"], initial_condition_file),
              _dbg_string, "debug")

    # - Opening the file -#
    snapshot = pyn.load(
        os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"], initial_condition_file))

    # - grabbing the preliminary interesting data -#
    report_data["General"]["N Particles"] = np.format_float_scientific(len(snapshot),
                                                                       precision=3)  # recording the total number of particles
    report_data["General"]["Families"] = [fam.name for fam in snapshot.families()]
    report_data["General"]["Loadable_keys"] = [key for key in snapshot.loadable_keys()]
    report_data["General"]["Mass"] = str(
        np.format_float_scientific(np.sum(snapshot["mass"].in_units(CONFIG["units"]["default_mass_unit"])),
                                   precision=3)) + " %s" % CONFIG["units"]["default_mass_unit"]

    # - Giving family level general data -#
    for family in snapshot.families():
        report_data["General"][family.name] = {}
        report_data["General"][family.name]["N Particles"] = np.format_float_scientific(len(snapshot[family]),
                                                                                        precision=3)
        report_data["General"][family.name]["Loadable_keys"] = [key for key in snapshot[family].loadable_keys()]
        report_data["General"][family.name]["Mass"] = str(np.format_float_scientific(
            np.sum(snapshot[family]["mass"].in_units(CONFIG["units"]["default_mass_unit"])), precision=3)) + " %s" % \
                                                      CONFIG["units"][
                                                          "default_mass_unit"]
    # Managing binary files
    ####################################################################################################################
    if log_data["type"] == "cluster-binary":  # the IC file has a binary collision.
        # Splitting the binaries
        ################################################################################################################
        binary_coms = find_gas_COM(snapshot, 0.001)
        binary_snapshots = split_binary_collision(snapshot)

        for subsnap, id, com in zip(binary_snapshots, ["1", "2"], binary_coms):
            report_data["Cluster %s" % id] = {}
            report_data["Cluster %s" % id]["N Particles"] = np.format_float_scientific(len(subsnap),
                                                                                       precision=3)  # recording the total number of particles
            report_data["Cluster %s" % id]["Families"] = [fam.name for fam in subsnap.families()]
            report_data["Cluster %s" % id]["Loadable_keys"] = [key for key in subsnap.loadable_keys()]
            report_data["Cluster %s" % id]["COM"] = [str(i) + " %s" % CONFIG["units"]["default_length_unit"] for i in
                                                     list(com.in_units(CONFIG["units"]["default_length_unit"]))]
            report_data["Cluster %s" % id]["COM-Velocity"] = [str(i) + " %s" % CONFIG["units"]["default_velocity_unit"]
                                                              for i in list(
                    pyn.analysis.halo.center_of_mass_velocity(subsnap).in_units(
                        CONFIG["units"]["default_velocity_unit"]))]
            report_data["Cluster %s" % id]["Mass"] = str(np.format_float_scientific(
                np.sum(subsnap["mass"].in_units(CONFIG["units"]["default_mass_unit"])))) + " %s" % \
                                                     CONFIG["units"][
                                                         "default_mass_unit"]
            # - Giving family level general data -#
            for family in subsnap.families():
                report_data["Cluster %s" % id][family.name] = {}
                report_data["Cluster %s" % id][family.name]["N Particles"] = np.format_float_scientific(
                    len(subsnap[family]), precision=3)
                report_data["Cluster %s" % id][family.name]["Loadable_keys"] = [key for key in
                                                                                subsnap[family].loadable_keys()]
                report_data["Cluster %s" % id][family.name]["Mass"] = str(np.format_float_scientific(
                    np.sum(subsnap[family]["mass"].in_units(CONFIG["units"]["default_mass_unit"])),
                    precision=3)) + " %s" % \
                                                                      CONFIG["units"][
                                                                          "default_mass_unit"]
    else:
        # - This isn't a binary -#
        pass

    # Writing the report file
    ####################################################################################################################
    report_dir = os.path.join(CONFIG["system"]["directories"]["reports_directory"],
                              initial_condition_file.split(".")[0])
    report_name = datetime.now().strftime('%m-%d-%Y_%H-%M')
    if not os.path.isdir(report_dir):
        pt.Path.mkdir(pt.Path(report_dir), parents=True)

    os.mkdir(os.path.join(report_dir, report_name))

    with open(os.path.join(report_dir, report_name, "report.txt"), "w+") as file:
        toml.dump(report_data, file)
    ####################################################################################################################
    #
    #   Finished writing the bulk of the report data. Now we produce the profiles.
    #
    ####################################################################################################################
    # Computing the correct profiles for the given IC
    ####################################################################################################################
    #- fetching the parameter files -#
    params_files = log_data["param_files"] # grab the parameter file locations.

    #- grabbing the data from the parameter files
    parameter_data = [read_clustep_ini(file) for file in params_files] # reading

    # Managing profiles
    ####################################################################################################################
    if not log_data["type"] == "cluster-binary":
        # - This is not a binary, so we pass through as usual.
        save_location = os.path.join(report_dir, report_name, "%s.png")
        for key, value in __profile_config.items():  # cycle through all of the profile items.
            make_profile_plot(
                snapshot,
                key,
                save=True,
                end_file=save_location % key,
                Lambda=get_theoretical_lambda(key,parameter_dict=deepcopy(parameter_data[0]),**value),
                Lambda_label="%s (Theory)"%value["title"],
                **value,
                **__line_config
            )
            #- Creating the multi-pass profiles -#
        for plot in __multi_profile_config:
            ##- Managing lambdas -##
            for group in plot["dat"]:
                group["q_kwargs"]["Lambda"]=get_theoretical_lambda(group["quantity"],
                                                                    parameter_dict=deepcopy(parameter_data[0]),
                                                                    **group["q_kwargs"])
                group["q_kwargs"]["Lambda_label"] = group["q_kwargs"]["label"] + " (Theory)"
            make_profiles_plot(
                snapshot,
                plot["dat"],
                save=True,
                end_file=save_location % plot["name"],
                **plot["kwargs"]
            )
    else:
        # - This is not a binary, so we pass through as usual.
        save_location = os.path.join(report_dir, report_name, "%s_%s.png")

        for subsnap, id in zip(binary_snapshots, ["1", "2"]):
            for key, value in __profile_config.items():  # cycle through all of the profile items.
                make_profile_plot(
                    subsnap,
                    key,
                    save=True,
                    end_file=save_location % (key, id),
                    Lambda=get_theoretical_lambda(key, parameter_dict=deepcopy(parameter_data[int(id)-1]), **value),
                    Lambda_label="%s (Theory)" % value["title"],
                    **value,
                    **__line_config
                )
                # - Creating the multi-pass profiles -#
            for plot in __multi_profile_config:
                for group in plot["dat"]:
                    group["q_kwargs"]["Lambda"] = get_theoretical_lambda(group["quantity"],
                                                                         parameter_dict=deepcopy(parameter_data[int(id)-1]),
                                                                         **group["q_kwargs"])
                    group["q_kwargs"]["Lambda_label"] = group["q_kwargs"]["label"] + " (Theory)"
                make_profiles_plot(
                    subsnap,
                    plot["dat"],
                    save=True,
                    end_file=save_location % (plot["name"], id),
                    **plot["kwargs"]
                )
    # Adding Images
    ####################################################################################################################
    snapshot = pyn.load(
        os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"], initial_condition_file))
    snapshot.g["smooth"] = pyn.sph.smooth(snapshot.g)
    snapshot.g["rho"] = pyn.sph.rho(snapshot.g)
    save_location = os.path.join(report_dir, report_name, "I-%s.png")

    #- Generating the temperature image -#
    make_plot(snapshot,
              "temp",
              families=["gas"],
              save=True,
              end_file=save_location % "temp",
              log=False,
              vmin=0.01,
              width="%s kpc" % int(2 * np.amax(snapshot["pos"][:, 0].in_units("kpc"))),
              title="Gas Temperature",
              cmap=plt.cm.jet,
              av_z=True)

    #- Generating the density image -#
    make_plot(snapshot,
              "rho",
              save=True,
              end_file=save_location % "density",
              width="%s kpc" % int(2 * np.amax(snapshot["pos"][:, 0].in_units("kpc"))),
              title="Density",
              log=True,
              vmin=133,
              cmap=plt.cm.viridis,
              av_z=True)
