"""

Grabs a report on a specified IC file.
    Written by: Eliza Diggins
"""
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from copy import deepcopy
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print, make_error
import pathlib as pt
from PyCS_System.SimulationMangement import ICLog
from PyCS_System.SpecConfigs import read_clustep_ini
import toml
from datetime import datetime
import pynbody as pyn
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import host_subplot
from mpl_toolkits import axisartist
from matplotlib.lines import Line2D
import numpy as np
from PyCS_System.text_utils import file_select, print_title
from PyCS_Analysis.Images import make_plot
from PyCS_Analysis.Profiles import make_profile_plot, make_profiles_plot
from PyCS_Analysis.Analysis_Utils import split_binary_collision, find_gas_COM
from PyCS_Analysis.builtin_functions import dehnen_profile, dehnen_mass_profile, get_collision_parameters, find_rx, \
    rho_critical
from colorama import Fore, Style
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Tools"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s: " % (_location, _filename)
CONFIG = read_config(_configuration_path)
iclog = ICLog.load_default()
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Static Vars -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# Profile config contains all of the profiles we generate in the process of building the report.
__profile_config = {
    "density": {
        "logx": True,
        "logy": True,
        "title": "Cluster Density",
        "units_x": "kpc"
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
                       "Lambda": lambda x: x ** 3}
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
def get_theoretical_lambda(qty, parameter_dict, **kwargs):
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
    fdbg_string = "%s:get_theoretical_lambda: " % _dbg_string
    log_print("Generating %s profile for the given IC file." % qty, fdbg_string, "debug")
    # Setup
    ####################################################################################################################
    # - Coercing family kwargs into the correct form for this use -#
    family = []
    if "family" in kwargs:
        if kwargs["family"] != "gas":
            # the family is specified, but isn't gas. We expect this case to be "dm" from the __param_dicts, but we need to change it.
            family = ["dark_matter"]
        elif kwargs["family"] == "gas":
            family = ["gas"]
    else:
        family = ["gas", "dark_matter"]

    # - unit_fetch and coercion
    # here we control all of the parameter data in order to get the right units.
    parameter_dict["gas"]["M_gas"] = parameter_dict["gas"]["M_gas"] * (1e10) * pyn.units.Unit("Msol")
    parameter_dict["gas"]["a_gas"] = parameter_dict["gas"]["a_gas"] * (pyn.units.Unit("kpc"))
    parameter_dict["dark_matter"]["M_dm"] = parameter_dict["dark_matter"]["M_dm"] * (1e10) * pyn.units.Unit("Msol")
    parameter_dict["dark_matter"]["a_dm"] = parameter_dict["dark_matter"]["a_dm"] * (pyn.units.Unit("kpc"))

    kwgs = {}
    if "units_x" in kwargs:
        kwgs["independent_unit"] = kwargs["units_x"]
    if "units_y" in kwargs:
        kwgs["dependent_unit"] = kwargs["units_y"]
    # Generating the correct profiles
    ####################################################################################################################
    lambdas = []
    under_labels = {"gas": "gas", "dark_matter": "dm"}
    # - generating the functions -#
    for fam in family:  # cycle through all of the families
        if qty == "density":
            # - Managing the Dehnen profile -#
            lambdas.append(dehnen_profile(parameter_dict[fam]["M_%s" % under_labels[fam]],
                                          parameter_dict[fam]["gamma_%s" % under_labels[fam]],
                                          parameter_dict[fam]["a_%s" % under_labels[fam]],
                                          **kwgs))
        elif qty == "mass_enc":
            lambdas.append(dehnen_mass_profile(parameter_dict[fam]["M_%s" % under_labels[fam]],
                                               parameter_dict[fam]["gamma_%s" % under_labels[fam]],
                                               parameter_dict[fam]["a_%s" % under_labels[fam]],
                                               **kwgs))
        else:
            return None

    # Returning
    ####################################################################################################################
    if len(lambdas) > 1:
        return lambda r: np.sum([l(r) for l in lambdas], axis=0)
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

    # - Print string -#
    fdbg_string = Fore.GREEN + Style.BRIGHT + _dbg_string + Style.RESET_ALL
    done_string = "[%s]" % (Fore.CYAN + Style.BRIGHT + "DONE" + Style.RESET_ALL)
    # Selecting an IC file
    ####################################################################################################################
    initial_condition_file = file_select(CONFIG["system"]["directories"]["initial_conditions_directory"],
                                         conditions=lambda fn: any(i in fn for i in [".dat", ".g2", ".g1"]))
    report_dir = os.path.join(CONFIG["system"]["directories"]["reports_directory"],
                              initial_condition_file.split(".")[0])
    report_name = datetime.now().strftime('%m-%d-%Y_%H-%M')
    if not os.path.isdir(report_dir):
        pt.Path.mkdir(pt.Path(report_dir), parents=True)

    os.mkdir(os.path.join(report_dir, report_name))
    # Reading from the IC log
    ####################################################################################################################
    if not initial_condition_file in iclog:  # we don't have an entry.
        make_error(ValueError, _dbg_string, "Failed to find an IC log entry for %s." % initial_condition_file)
        exit()
    else:
        log_data = iclog[initial_condition_file]  # fetching iclog for the given entry.

    print("%sLoading initial condition log data for %s...\t%s" % (fdbg_string, initial_condition_file, done_string))
    # Opening the IC file and grabbing preliminary data
    ####################################################################################################################
    #
    # ----> This is global data that applies to all IC files regardless of form.
    #

    log_print("Attempting to open the selected file at %s." % os.path.join(
        CONFIG["system"]["directories"]["initial_conditions_directory"], initial_condition_file),
              _dbg_string, "debug")

    # - Opening the file -#
    print("%sLoading initial condition snapshot...\t" % fdbg_string, end="")
    snapshot = pyn.load(
        os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"], initial_condition_file))
    print(done_string)
    # - grabbing the preliminary interesting data -#

    print("%sGathering general data..." % fdbg_string, end="")
    report_data["General"]["N Particles"] = np.format_float_scientific(len(snapshot),
                                                                       precision=3)  # recording the total number of particles
    report_data["General"]["Families"] = [fam.name for fam in snapshot.families()]
    report_data["General"]["Loadable_keys"] = [key for key in snapshot.loadable_keys()]
    report_data["General"]["Mass"] = str(
        np.format_float_scientific(np.sum(snapshot["mass"].in_units(CONFIG["units"]["default_mass_unit"])),
                                   precision=3)) + " %s" % CONFIG["units"]["default_mass_unit"]

    print(done_string)
    # - Giving family level general data -#
    for family in snapshot.families():
        print("\t%sGathering general data for family %s..." % (fdbg_string, family), end="")
        report_data["General"][family.name] = {}
        report_data["General"][family.name]["N Particles"] = np.format_float_scientific(len(snapshot[family]),
                                                                                        precision=3)
        report_data["General"][family.name]["Loadable_keys"] = [key for key in snapshot[family].loadable_keys()]
        report_data["General"][family.name]["Mass"] = str(np.format_float_scientific(
            np.sum(snapshot[family]["mass"].in_units(CONFIG["units"]["default_mass_unit"])), precision=3)) + " %s" % \
                                                      CONFIG["units"][
                                                          "default_mass_unit"]
        print(done_string)
    # Managing binary files
    ####################################################################################################################
    if log_data["type"] == "cluster-binary":  # the IC file has a binary collision.
        print("%sFile recognized as a cluster-binary. Generating binary data..." % fdbg_string, end="")
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
        print(done_string)
        # Managing collision data
        ################################################################################################################
        print("%sGenerating collision data..." % fdbg_string, end="")

        # - grabbing the necessary data -#
        # getting the critical radii
        r_ns = [[find_rx(snap, p=p) for snap in binary_snapshots] for p in
                [2500 * rho_critical, 1000 * rho_critical, 500 * rho_critical, 200 * rho_critical]]
        rs = [r[0] + r[1] for r in r_ns]

        relative_location = [binary_coms[1][i] - binary_coms[0][i] for i in range(3)]
        initial_distance, impact_parameter = relative_location[0] * binary_coms[1].units, relative_location[1] * \
                                             binary_coms[1].units
        masses = [np.sum(subsnap["mass"]) for subsnap in binary_snapshots]

        com_velocities = [pyn.analysis.halo.center_of_mass_velocity(snap) for snap in binary_snapshots]

        velocity = (com_velocities[1] - com_velocities[0])[0] * com_velocities[0].units

        # - making events -#
        event1 = lambda t, y: y[0] - float(rs[0].in_units("km"))
        event2 = lambda t, y: y[0] - float(rs[1].in_units("km"))
        event3 = lambda t, y: y[0] - float(rs[2].in_units("km"))
        event4 = lambda t, y: y[0] - float(rs[3].in_units("km"))
        event1.terminal = True

        # - compiling data -#
        data = get_collision_parameters(masses, impact_parameter, velocity, initial_distance,
                                        events=[event1, event2, event3, event4])

        # - gathering data -#
        r_2500_events, r_1000_events, r_500_events, r_200_events = tuple(
            (i, j, k) for i, j, k in zip(data.t_events, data.y_events, data.com_y_events))

        r_events = [item for item in [r_2500_events, r_1000_events, r_500_events, r_200_events] if len(item[0]) != 0]
        r_labels = [item for id, item in enumerate([2500, 1000, 500, 200]) if
                    len([r_2500_events, r_1000_events, r_500_events, r_200_events][id]) != 0]

        # Adding to report
        ################################################################################################################
        # - adding r_n values -#
        for r_n, type in zip(r_ns, [2500, 1000, 500, 200]):
            for cluster_id, r in zip(["1", "2"], r_n):
                report_data["Cluster %s" % cluster_id]["r_%s" % type] = "%s %s" % (
                np.round(r.in_units("kpc"), decimals=2), "kpc")

        for event, type in zip(r_events, r_labels):
            report_data["General"]["Collision Time (r_%s)" % type] = str(
                ["%s " % np.round(i, decimals=2, ) for i in event[0]]) + " Gyr"
            report_data["General"]["Relative Collision Velocity (r_%s)" % type] = str(
                ["%s " % np.round(i[1], decimals=2, ) for i in event[1]]) + " km s^-1"
        # Generating and saving the correct plots
        ################################################################################################################
        # - trajectory plot -#
        fig = plt.figure(figsize=CONFIG["Visualization"]["default_figure_size"])
        axes = fig.add_subplot(111)

        ##- plotting -##
        legend_handles = []  # We are going to use this to populate the legend.
        axes.plot(data.com_y[0] * np.cos(data.y[2]), data.com_y[0] * np.sin(data.y[2]), color="red")
        axes.plot(data.com_y[1] * np.cos(data.y[2]), data.com_y[1] * np.sin(data.y[2]), color="blue")
        axes.plot(data.com_y[0][0] * np.cos(data.y[2][0]), data.com_y[0][0] * np.sin(data.y[2][0]), "o", color="red")
        axes.plot(data.com_y[1][0] * np.cos(data.y[2][0]), data.com_y[1][0] * np.sin(data.y[2][0]), "o", color="blue")

        legend_handles += [Line2D([], [], color="red", label=r"$C_1$"), Line2D([], [], color="blue", label=r"$C_2$")]
        ##- adding events -##
        markers = ["x", "o", "d", ">"]
        labels = [r"$R_{\mathrm{%s}}\;\mathrm{col.}\;t=%s \mathrm{Gyr}$" % (i, "%s") for i in r_labels]
        for event, marker, label in zip(r_events, markers, labels):
            # Now we need to add the correct positions.
            event_t, event_y, event_com = event  # split the event down to the singular parts.
            for instance_t, instance_y, instance_com in zip(event_t, event_y, event_com):
                axes.scatter(instance_com[0] * np.cos(instance_y[2]), instance_com[0] * np.sin(instance_y[2]),
                             marker=marker, label="Cluster 1", color="red")
                axes.scatter(instance_com[1] * np.cos(instance_y[2]), instance_com[1] * np.sin(instance_y[2]),
                             marker=marker, label="Cluster 1", color="blue")

                # managing the time labels #
            time = np.round(event_t[0], decimals=2)
            legend_handles += [Line2D([], [], color="black", marker=marker, label=label % time)]
        ##- asthetics -##
        axes.set_xlabel(r"$x$ [kpc]")
        axes.set_xlabel(r"$y$ [kpc]")
        axes.set_title("Collision-less COM trajectories")
        axes.set_xlim([-initial_distance.in_units("kpc"), initial_distance.in_units("kpc")])
        axes.set_ylim([-initial_distance.in_units("kpc"), initial_distance.in_units("kpc")])
        plt.grid()
        plt.legend(handles=legend_handles)
        plt.savefig(os.path.join(report_dir, report_name, "Collision_trajectory.png"))

        # - time_distance plot -#
        fig = plt.figure(figsize=CONFIG["Visualization"]["default_figure_size"])
        axes = host_subplot(111, axes_class=axisartist.Axes)
        axes2 = axes.twinx()

        ##- plotting -##
        axes.plot(data.t, data.y[0], label=r"$\mathbf{r}(t)$", color="red")
        axes.plot(data.t[0], data.y[0][0], "o", color="red", label=r"$\mathrm{C}_{1,\mathrm{init}}$")
        axes.plot(data.t[-1], data.y[0][-1], "s", color="red", label=r"$\mathrm{C}_{2,\mathrm{final}}$")
        axes2.plot(data.t, data.y[1], label=r"$\mathbf{v}(t)$", color="blue")
        axes2.plot(data.t[0], data.y[1][0], "o", color="blue", label=r"$\mathrm{C}_{1,\mathrm{init}}$")
        axes2.plot(data.t[-1], data.y[1][-1], "s", color="blue", label=r"$\mathrm{C}_{2,\mathrm{final}}$")

        ##- adding critical rs -##
        for r, n, ls in zip(rs, [2500, 1000, 500, 200], ["-", "-.", "--", ":"]):
            axes.hlines(xmin=0, xmax=1.2 * np.amax(data.t), y=r.in_units("kpc"), label=r"$\sum r_{%s}$" % n, ls=ls,
                        color="black")
        ##- asthetics -##
        axes2.axis["right"].toggle(all=True)
        axes.set_xlabel(r"$t$ [Gyr]")
        axes.set_ylabel(r"$y$ [kpc]")
        axes2.set_ylabel(r"$|\mathbf{v}(t)|\;\left[\mathrm{km}\;\mathrm{s}^{-1}\right]$")
        axes.set_title("Relative radial trajectory")
        axes.set_xlim([0, 1.2 * np.amax(data.t)])
        axes.set_ylim([0, initial_distance.in_units("kpc")])
        plt.grid()
        axes.legend()
        plt.savefig(os.path.join(report_dir, report_name, "radial_trajectory.png"))

        print(done_string)
    else:
        # - This isn't a binary -#
        pass

    # Writing the report file
    ####################################################################################################################
    print("%sWriting report..." % fdbg_string, end="")

    with open(os.path.join(report_dir, report_name, "report.txt"), "w+") as file:
        toml.dump(report_data, file)

    print(done_string)
    print("%sGathering generating plot parameter files..." % fdbg_string, end="")
    ####################################################################################################################
    #
    #   Finished writing the bulk of the report data. Now we produce the profiles.
    #
    ####################################################################################################################
    # Computing the correct profiles for the given IC
    ####################################################################################################################
    # - fetching the parameter files -#
    params_files = log_data["param_files"]  # grab the parameter file locations.

    # - grabbing the data from the parameter files
    parameter_data = [read_clustep_ini(file) for file in params_files]  # reading
    print(done_string)
    # Managing profiles
    ####################################################################################################################
    if not log_data["type"] == "cluster-binary":
        # - This is not a binary, so we pass through as usual.
        save_location = os.path.join(report_dir, report_name, "%s.png")
        for key, value in __profile_config.items():  # cycle through all of the profile items.
            print("%sPlotting %s profile...\t" % (fdbg_string, value["title"]), end="")
            make_profile_plot(
                snapshot,
                key,
                save=True,
                end_file=save_location % key,
                Lambda=get_theoretical_lambda(key, parameter_dict=deepcopy(parameter_data[0]), **value),
                Lambda_label="%s (Theory)" % value["title"],
                **value,
                **__line_config
            )
            print(done_string)
            # - Creating the multi-pass profiles -#
        for plot in __multi_profile_config:
            ##- Managing lambdas -##
            print("%sPlotting group %s...\t" % (fdbg_string, plot["name"]), end="")
            for group in plot["dat"]:
                group["q_kwargs"]["Lambda"] = get_theoretical_lambda(group["quantity"],
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
            print(done_string)
    else:
        # - This is not a binary, so we pass through as usual.
        save_location = os.path.join(report_dir, report_name, "%s_%s.png")

        for subsnap, id in zip(binary_snapshots, ["1", "2"]):
            for key, value in __profile_config.items():  # cycle through all of the profile items.
                print("%sPlotting %s profile for subsnap %s...\t" % (fdbg_string, value["title"], id), end="")
                make_profile_plot(
                    subsnap,
                    key,
                    save=True,
                    end_file=save_location % (key, id),
                    Lambda=get_theoretical_lambda(key, parameter_dict=deepcopy(parameter_data[int(id) - 1]), **value),
                    Lambda_label="%s (Theory)" % value["title"],
                    **value,
                    **__line_config
                )
                print(done_string)
                # - Creating the multi-pass profiles -#
            for plot in __multi_profile_config:
                print("%sPlotting group %s for subsnap %s...\t" % (fdbg_string, plot["name"], id), end="")
                for group in plot["dat"]:
                    group["q_kwargs"]["Lambda"] = get_theoretical_lambda(group["quantity"],
                                                                         parameter_dict=deepcopy(
                                                                             parameter_data[int(id) - 1]),
                                                                         **group["q_kwargs"])
                    group["q_kwargs"]["Lambda_label"] = group["q_kwargs"]["label"] + " (Theory)"
                make_profiles_plot(
                    subsnap,
                    plot["dat"],
                    save=True,
                    end_file=save_location % (plot["name"], id),
                    **plot["kwargs"]
                )
                print(done_string)
    # Adding Images
    ####################################################################################################################
    snapshot = pyn.load(
        os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"], initial_condition_file))
    snapshot.g["smooth"] = pyn.sph.smooth(snapshot.g)
    snapshot.g["rho"] = pyn.sph.rho(snapshot.g)
    save_location = os.path.join(report_dir, report_name, "I-%s.png")

    # - Generating the temperature image -#
    print("%sGenerating temperature image.\t" % (fdbg_string), end="")
    make_plot(snapshot,
              "temp",
              families=["gas"],
              save=True,
              end_file=save_location % "temp",
              log=False,
              vmin=0.01,
              width="%s kpc" % int(2 * np.amax(snapshot["pos"][:, 0].in_units("kpc"))),
              title="Gas Temperature",
              cmap=plt.cm.gist_ncar,
              av_z=False)
    make_plot(snapshot,
              "temp",
              families=["gas"],
              save=True,
              end_file=save_location % "temp-I",
              log=False,
              vmin=0.01,
              width="%s kpc" % int(2 * np.amax(snapshot["pos"][:, 0].in_units("kpc"))),
              title="Gas Temperature",
              cmap=plt.cm.gist_ncar,
              av_z=True)
    print(done_string)
    print("%sGenerating density image.\t" % (fdbg_string), end="")
    # - Generating the density image -#
    make_plot(snapshot,
              "rho",
              save=True,
              end_file=save_location % "density",
              width="%s kpc" % int(2 * np.amax(snapshot["pos"][:, 0].in_units("kpc"))),
              title="Density",
              log=True,
              vmin=133,
              cmap=plt.cm.inferno,
              av_z=False)
    make_plot(snapshot,
              "rho",
              save=True,
              end_file=save_location % "density-I",
              width="%s kpc" % int(2 * np.amax(snapshot["pos"][:, 0].in_units("kpc"))),
              title="Density",
              log=True,
              vmin=133,
              cmap=plt.cm.inferno,
              av_z=True)
    print(done_string)
