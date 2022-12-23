"""

    Functions having to do with profiles and plots of data extracted from simulations.

"""
### Imports ###
# adding the system path to allow us to import the important modules
import os
import sys
import pathlib as pt
import numpy as np
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_Analysis.Analysis_Utils import get_families, align_snapshot
from PyCS_Core.PyCS_Errors import *
import matplotlib.pyplot as plt
from PyCS_System.SimulationMangement import get_simulation_qty
from utils import split
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import current_process
import matplotlib as mpl
import gc

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

##- Setting up TEX if it is configured -##
try:
    if CONFIG["Visualization"]["use_tex"]:
        plt.rcParams['text.usetex'] = True
        plt.rcParams['xtick.major.size'] = 8
        plt.rcParams['xtick.minor.size'] = 5
        plt.rcParams['ytick.major.size'] = 8
        plt.rcParams['ytick.minor.size'] = 5
        plt.rcParams['xtick.direction'] = "in"
        plt.rcParams['ytick.direction'] = "in"
except RuntimeError:
    log_print("Failed to load latex.", _dbg_string, "error")

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

#----# PYNBODY KWARGS DEFAULT #----------------------------------------------------------------------------------------#
#   These are used by the plotting functions as the basic input kwargs for the plotting functions. They are added
#   to the input kwargs to create a standardized set of always passed kwargs.
#
__pynbody_profile_defaults = {
    "ndim": CONFIG["analysis"]["profiles"]["profile_ndim"],
    "nbins": CONFIG["analysis"]["profiles"]["nbins"],
    "type": CONFIG["analysis"]["profiles"]["type"],
    "rmin": None,
    "rmax": None
} # Kwargs to pass through pyn.analysis.profile.Profile

#---# QUANTITY SPECIFIC DEFAULTS #-------------------------------------------------------------------------------------#
#   These dictionaries carry kwargs specific to each quantity that gets passed into either the profiles or
#   the pyn.plot.sph.image() function.
#
__quantities = {
    "vx": {
        "unit": CONFIG["units"]["default_velocity_unit"],
        "fancy": "x Velocity",
        "families": ["gas", "stars", "dm"]
    },
    "vy": {
        "unit": CONFIG["units"]["default_velocity_unit"],
        "fancy": "y Velocity",
        "families": ["gas", "stars", "dm"]
    },
    "vz": {
        "unit": CONFIG["units"]["default_velocity_unit"],
        "fancy": "z Velocity",
        "families": ["gas", "stars", "dm"]
    },
    "temp": {
        "unit": CONFIG["units"]["default_temperature_unit"],
        "fancy": "Temperature",
        "families": ["gas"]
    },
    "density": {
        "unit": CONFIG["units"]["default_density_unit"],
        "fancy": "Density",
        "families": ["gas", "stars", "dm"]
    },
    "mass_enc": {
        "unit": CONFIG["units"]["default_mass_unit"],
        "fancy": "Enclosed Mass",
        "families": ["gas", "stars", "dm"]
    },
    "dyntime": {
        "unit": "Myr",
        "fancy": "Dynamical Time",
        "families": ["gas", "stars", "dm"]
    },
    "g_spherical": {
        "unit": "m s^-2",
        "fancy": "Spherical Potential",
        "families": ["gas", "stars", "dm"]
    },
    "p": {
        "unit": "N m^-2",
        "fancy": "Pressure",
        "families": ["gas"]
    }
}

#---# PHYSICAL CONSTANTS #---------------------------------------------------------------------------------------------#
boltzmann = 1.380649e-23 * pyn.units.Unit("J K^-1")  # Defining the Boltzmann constant


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Minor Functions -------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

def set_units(qty):
    """
    Sets the correct default unit for the given qty.
    Parameters
    ----------
    qty: The qty string.

    Returns: The correct unit.
    -------

    """
    return pyn.units.Unit(__quantities[qty]["unit"])


def fancy_qty(qty):
    """
    Prints a fancy string for the given quantity.
    Parameters
    ----------
    qty

    Returns
    -------

    """
    return __quantities[qty]["fancy"]



def fix_array_u(array, qty, units):
    """
    Run on all outputting arrays using the fixed units and the quantity. This can be used to correct for issues in the array ahead of time.
    **UNIT-ED**
    Parameters
    ----------
    array: The array to fix.
    qty: The quantity to use.
    units: The units that we actually want to use.

    Returns: fixed array.
    -------

    """
    if qty == "temp" and units != "K":
        return array * float(boltzmann.in_units("%s K^-1" % units)) * pyn.units.Unit(units)
    else:
        return array


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------- Multi-Processing Functions ----------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Sub-Functions -----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def make_profile_plot(snapshot,
                      qty,
                      Lambda=None,
                      Lambda_label=None,
                      profile=None,
                      save=CONFIG["Visualization"]["default_figure_save"],
                      end_file=CONFIG["system"]["directories"]["figures_directory"],
                      **kwargs):
    """
    Plots the ``qty`` profile of the input ``snapshot``. User can select an additional ``Lambda`` and ``Lambda_label`` to
    overlay on the plot.
    Parameters
    ----------
    profile: (*optional*) Provide a profile to avoid recalculating in repeated runs.

    snapshot: The snapshot to analyze.

    qty: The quantity to plot.

    Lambda: (*optional*) Additional lambda function to overlay. Should be a function of **default** length units.

    Lambda_label: (*optional*) The label to assign to the ``Lambda`` input.

    save: True to save, False to show.

    end_file: The filename and path to which the figure should be saved.

    kwargs: additional kwargs for pyn.analysis.profile.Profile and plt.plot.

    Returns: None
    -------

    """
    # Intro Debugging
    ####################################################################################################################
    fdbg_string = "%smake_profile_plot: " % _dbg_string
    log_print("Generating %s profile plot for snapshot %s." % (qty, snapshot), fdbg_string, "debug")

    if "title" in kwargs:
        title = kwargs["title"]
        del kwargs["title"]
    else:
        title = ""
    # Creating the figure
    ####################################################################################################################
    fig = plt.figure(figsize=tuple(CONFIG["Visualization"]["default_figure_size"]))
    axes = fig.add_subplot(111)

    #- Generating the plot on the axes.
    data = _raw_make_profile_plot(snapshot,qty,Lambda=Lambda,Lambda_label=Lambda_label,profile=profile,axes=axes,**kwargs)

    #- pulling important info out of data -#
    x,y = tuple(data[1:])
    # - managing text -#
    axes.set_xlabel(r"Radius [$%s$]" % (x.units.latex()))  # setting the x axis
    axes.set_ylabel(r"%s [$%s$]" % (__quantities[qty]["fancy"], y.units.latex()))
    axes.set_title(title)

    # - adding a legend -#
    plt.legend()

    # - adding the grid -#
    plt.grid()

    # Saving
    #########################################################################################################################
    if save:
        plt.savefig(end_file)

        del profile
        axes.cla()
        del axes
        plt.figure().clear()
        plt.clf()
        plt.close('all')
        gc.collect()
    else:
        plt.show()

def make_profiles_plot(snapshot,
                      quantities:list,
                      profile=None,
                      save=CONFIG["Visualization"]["default_figure_save"],
                      end_file=CONFIG["system"]["directories"]["figures_directory"],
                      **kwargs):
    """
    Plots the ``qtys`` of the ``snapshot`` as well as overlayed ``Lambdas``.
    Parameters
    ----------
    profile: (*optional*) Provide a profile to avoid recalculating in repeated runs.

    snapshot: The snapshot to analyze.

    quantities: *dict* [{quantity:"",q_kwargs:{}}]

    Lambda: (*optional*) Additional lambda function to overlay. Should be a function of **default** length units.

    Lambda_label: (*optional*) The label to assign to the ``Lambda`` input.

    save: True to save, False to show.

    end_file: The filename and path to which the figure should be saved.

    kwargs: additional kwargs for pyn.analysis.profile.Profile and plt.plot.

    Returns: None
    -------

    """
    # Intro Debugging
    ####################################################################################################################
    fdbg_string = "%smake_profiles_plot: " % _dbg_string
    log_print("Generating %s profiles plot for snapshot %s." % (quantities, snapshot), fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    #- Title Management -#
    if "title" in kwargs:
        title = kwargs["title"]
        del kwargs["title"]
    else:
        title = ""

    #- Fixing quantities -#

    ##- Are units consistent? -##
    if len(list(set(list([__quantities[qty["quantity"]]["unit"] for qty in quantities])))) > 1:
        make_error(TypeError,fdbg_string,"Quantities %s are not compatible."%quantities)

    ##- Fixing internals -##
    for quantity in quantities:
        #- Checking that the keys all have a Lambda or None -#
        if not "Lambda" in quantity["q_kwargs"]:
            quantity["q_kwargs"]["Lambda"] = None
            quantity["q_kwargs"]["Lambda_label"]=None
        elif not "Lambda_Label" in quantity["q_kwargs"]:
            quantity["q_kwargs"]["Lambda_label"]=None

        #- managing kwargs in the main set that need to be moved to the output set -#
        if "logx" in kwargs:
            quantity["q_kwargs"]["logx"] = kwargs["logx"]
        if "logy" in kwargs:
            quantity["q_kwargs"]["logy"] = kwargs["logy"]
        if "units_y" in kwargs:
            quantity["q_kwargs"]["units_y"] = kwargs["units_y"]
        if "units_x" in kwargs:
            quantity["q_kwargs"]["units_x"] = kwargs["units_x"]

    print(quantities)
    # Creating the figure
    ####################################################################################################################
    fig = plt.figure(figsize=tuple(CONFIG["Visualization"]["default_figure_size"]))
    axes = fig.add_subplot(111)

    #- Generating the plot on the axes.
    for quantity in quantities:
        data = _raw_make_profile_plot(snapshot,
                                      quantity["quantity"],
                                      profile=profile,
                                      axes=axes,**quantity["q_kwargs"])

    #- pulling important info out of data -#
    x,y = tuple(data[1:])
    # - managing text -#
    axes.set_xlabel(r"Radius [$%s$]" % (x.units.latex()))  # setting the x axis
    if 'label_y' in kwargs:
        axes.set_ylabel(r"%s [$%s$]" % (kwargs["label_y"], y.units.latex()))
    else:
        axes.set_ylabel(r"%s [$%s$]" % (__quantities[quantities[0]["quantity"]]["fancy"], y.units.latex()))
    axes.set_title(title)
    # - adding a legend -#
    plt.legend()

    # - adding the grid -#
    plt.grid()

    # Saving
    #########################################################################################################################
    if save:
        plt.savefig(end_file)

        del profile
        axes.cla()
        del axes
        plt.figure().clear()
        plt.clf()
        plt.close('all')
        gc.collect()
    else:
        plt.show()


def _raw_make_profile_plot(snapshot,
                      qty,
                      Lambda=None,
                      Lambda_label=None,
                      profile=None,
                      axes=None,
                      **kwargs):
    """
    Plots the ``qty`` profile of the input ``snapshot``. User can select an additional ``Lambda`` and ``Lambda_label`` to
    overlay on the plot.

    **_raw**: This function is designed to be attached to other axes and therefore has no management for text or titles.
    That functionality should be managed by a different function.


    Parameters
    ----------
    profile: (*optional*) Provide a profile to avoid recalculating in repeated runs.

    snapshot: The snapshot to analyze.

    qty: The quantity to plot.

    Lambda: (*optional*) Additional lambda function to overlay. Should be a function of **default** length units.

    Lambda_label: (*optional*) The label to assign to the ``Lambda`` input.

    save: True to save, False to show.

    end_file: The filename and path to which the figure should be saved.

    kwargs: additional kwargs for pyn.analysis.profile.Profile and plt.plot.

    Returns: None
    -------

    """
    # Intro Debugging
    ####################################################################################################################
    fdbg_string = "%s_raw_make_profile_plot: " % _dbg_string
    log_print("Generating %s profile plot for snapshot %s." % (qty, snapshot), fdbg_string, "debug")

    # Managing profile kwargs
    ####################################################################################################################
    _prof_kwargs = {}  # these are the kwargs we will pass in
    for key, value in __pynbody_profile_defaults.items():
        if key in kwargs:  # the user included it in their list.
            _prof_kwargs[key] = kwargs[key]
            del kwargs[key]
        else:  # not included in the inputted kwargs. We check for None, then add.
            if value != None:
                _prof_kwargs[key] = value
            else:  # These were set to nonetype anyways.
                pass

    # Creating the profile in question
    ####################################################################################################################
    if not profile:
        # - working out which families to generate the profile for -#
        if "family" in kwargs:
            # We have a family kwargs
            try:
                family = [snap_fam for snap_fam in snapshot.families() if snap_fam.name == kwargs['family']][
                    0]  # get the family
            except KeyError:
                # There was no family of this type.
                make_error(ValueError, fdbg_string, "Failed to recognize family input %s" % (kwargs["family"]))
                return None

            # - creating the profile -#
            profile = pyn.analysis.profile.Profile(snapshot[family], **_prof_kwargs)
            del kwargs["family"]
        else:
            # - creating the profile -#
            profile = pyn.analysis.profile.Profile(snapshot, **_prof_kwargs)

    # Attempting to generate plotted items
    ####################################################################################################################
    # - grabbing the x array -#
    x = profile["rbins"]  # grabbing the x-array

    if "units_x" in kwargs:
        x = x.in_units(kwargs["units_x"])
        del kwargs["units_x"]
    else:
        x = x.in_units(CONFIG["units"]["default_length_unit"])
    # - grabbing the y array -#
    try:
        # We need to fix this array to manage possible unit errors #
        y = fix_array_u(profile[qty], qty, (__quantities[qty]["unit"] if "unit_y" not in kwargs else kwargs["unit_y"]))
    except KeyError:
        make_error(ValueError, fdbg_string, "The quantity %s is not a valid quantity for this profile..." % qty)
        return None

    if qty != "temp":
        if "units_y" in kwargs:
            y = y.in_units(kwargs["units_y"])
            del kwargs["units_y"]
        else:
            y = y.in_units(__quantities[qty]["unit"])

    # Setting up plotting
    ####################################################################################################################
    # - grabbing kwargs -#
    # -- getting x-log information --#
    if "logx" in kwargs and kwargs["logx"] == True:
        logx = True
        del kwargs["logx"]
    elif "logx" in kwargs:
        logx = False
        del kwargs["logx"]
    else:
        logx = False

    # -- getting y-log information --#
    if "logy" in kwargs and kwargs["logy"] == True:
        logy = True
        del kwargs["logy"]
    elif "logy" in kwargs:
        logy = False
        del kwargs["logy"]
    else:
        logy = False


    if "label" not in kwargs:
        kwargs["label"] = __quantities[qty]["fancy"]
    # Plotting
    ####################################################################################################################
    # - creating the figure -#
    if not axes:
        fig = plt.figure(figsize=tuple(CONFIG["Visualization"]["default_figure_size"]))
        axes = fig.add_subplot(111)

    # - Finding plotting function -#
    if logx and logy:
        plt_func = axes.loglog
    elif logx:
        plt_func = axes.semilogx
    elif logy:
        plt_func = axes.semilogy
    else:
        plt_func = axes.plot

    # - creating the actual plot -#
    plt_func(x, y, **kwargs)

    ##-managing the lambda function -##
    if Lambda != None:  # there is a lambda function
        l_kwargs = {key:value for key,value in kwargs.items() if key in ["color","lw"]}
        l_kwargs["ls"] = ":"
        plt_func(x, Lambda(x), label=(Lambda_label if Lambda_label else ""),**l_kwargs)


    # Returning
    ####################################################################################################################
    return [axes,x,y]

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#


# Functions for generating profiles
# ----------------------------------------------------------------------------------------------------------------------#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -----------------------------------------------------   MAIN   --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="STDOUT", level=10)
    data = pyn.load("/home/ediggins/PyCS/initial_conditions/Clu_2.dat")
    data.g["smooth"] = pyn.sph.smooth(data.g)
    data.g["rho"] = pyn.sph.rho(data.g)
    make_profiles_plot(data,[{
            "quantity":"density",
            "q_kwargs":{"color":"black","Lambda":lambda x: x**2,"label":"Total Density"}},{"quantity":"density",
            "q_kwargs":{"family":"gas","color":"r"}}],save=False,logy=True,logx=True,units_x="km",title="temp_title")
    fig = plt.figure()
    axes = fig.add_subplot(111)
    _raw_make_profile_plot(data,"density",axes=axes,family="gas",logx=True,logy=True)
    _raw_make_profile_plot(data,"density",axes=axes,logx=True,color="r",logy=True)
    plt.legend()
    plt.show()


