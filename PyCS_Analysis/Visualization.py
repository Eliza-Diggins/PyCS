"""

        PyCS Analysis Utils for common use

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

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

try:
    if CONFIG["Visualization"]["use_tex"]:
        plt.rcParams['text.usetex'] = True
        plt.rcParams['xtick.major.size'] = 8
        plt.rcParams['xtick.minor.size'] = 5
        plt.rcParams['ytick.major.size'] =8
        plt.rcParams['ytick.minor.size'] = 5
        plt.rcParams['xtick.direction'] ="in"
        plt.rcParams['ytick.direction'] ="in"
except RuntimeError:
    log_print("Failed to load latex.",_dbg_string,"error")

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
__pynbody_image_defaults = {  # This dictionary tracks the default kwargs to pass to pyn.plot.sph.image
    "cmap": CONFIG["Visualization"]["ColorMaps"]["default_image_colormap"],
    "resolution": CONFIG["Visualization"]["Images"]["default_resolution"],
    "width": CONFIG["Visualization"]["Images"]["default_width"]
}

__quantities = {
    "vx": {
        "unit":CONFIG["units"]["default_velocity_unit"],
        "fancy":"x Velocity",
        "families":["gas","stars","dm"]
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
    "rho": {
        "unit": CONFIG["units"]["default_density_unit"],
        "fancy": "Density",
        "families": ["gas"]
    }
}

### Constants ###
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


def fix_array(array, qty, units):
    """
    Run on all outputting arrays using the fixed units and the quantity. This can be used to correct for issues in the array ahead of time.

    Parameters
    ----------
    array: The array to fix.
    qty: The quantity to use.
    units: The units that we actually want to use.

    Returns: fixed array.
    -------

    """
    if qty == "temp" and units != "K":

        return array * boltzmann.in_units("%s K^-1" % units)
    else:
        return array


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------- Multi-Processing Functions ----------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Sub-Functions -----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# NOTES:
#    generate_image_array maps snapshots -> image arrays,
#       Then, make_plot maps -> snapshots -> images actually saved.
#
#
#
#
#
#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#
def generate_image_array(snapshot, qty, families=None, **kwargs):
    """
    Generates the plot array for a specific snapshot and quantity.
    Parameters
    ----------
    snapshot: The SimSnap object to use in the plotting.
    qty: The qty to plot.
    families: The families to include in the plot. Defaults to all.
    kwargs: Additional kwargs to pass to the plotting system.

    Returns: Numpy array.
    -------

    """
    # DEBUGGING
########################################################################################################################
    fdbg_string = _dbg_string + "generate_image_array: "
    log_print("Plotting %s for families %s and qty %s." % (qty, families, snapshot), fdbg_string, "debug")

    # KWARG MANAGEMENT
########################################################################################################################

    #- families -#

    if families:  # There are families, we need to get them to a usable format.
        families = get_families(snapshot, families)

        # checking for a reasonable length
        if not len(families):
            make_error(SnapshotError, fdbg_string, "Families %s were not found." % families)
    else:
        families = snapshot.families()
        print(families)


    #- Getting defaults -#

    for key, value in __pynbody_image_defaults.items():  # cycle through all of the defaults
        if key not in kwargs:
            kwargs[key] = value
        else:
            pass


    #- Managing units -#

    if "units" not in kwargs:  # there are not yet specified units
        kwargs["units"] = set_units(qty)

    # - Managing fix units -#

    if qty == "temp":  # ----> we feed this into the fix units function.
        fix_units = kwargs["units"]
        kwargs["units"] = pyn.units.Unit("K")
    else:
        fix_units = kwargs["units"]

    # PLOTTING
########################################################################################################################
    # - Generating the empty array -#
    output_array = np.zeros((kwargs["resolution"], kwargs["resolution"]))

    for family in families:
        ### Cycle through each family and generate the image array.
        try:
            output_array += pyn.plot.sph.image(snapshot[family], qty=qty, noplot=True, **kwargs,threaded=False)
            log_print("Plotted family %s for snapshot %s and quantity %s." % (family.name, snapshot, qty),
                      fdbg_string, "info")
        except Exception:
            log_print("Failed to plot family %s for snapshot %s and quantity %s." % (family.name, snapshot, qty),
                      fdbg_string, "error")

    # RETURNING
########################################################################################################################
    return fix_array(output_array, qty, fix_units)


def make_plot(snapshot,
              qty,
              families=None,
              save=CONFIG["Visualization"]["default_figure_save"],
              end_file=None,
              time_units=pyn.units.Unit(CONFIG["units"]["default_time_unit"]),
              title=None,
              length_units=CONFIG["units"]["default_length_unit"],
              **kwargs) -> None:
    """
    Plots the snapshot, qty and families. Saves to an intended location.
    Parameters
    ----------
    save: True to save, False to pass
    end_file: The endfile location.
    snapshot: The snapshot to pass in.
    qty: The qty to plot.
    families: The families to use.
    kwargs: Additional plotting kwargs.

    Returns: None
    -------

    """
    ### Intro Debugging ###
    fdbg_string = _dbg_string + "make:plot: "
    log_print("Making plot of %s for %s." % (qty, snapshot), fdbg_string, "debug")

    ### Managing defaults ###
    # Managing kwargs #
    for key, value in __pynbody_image_defaults.items():  # cycle through all of the defaults
        if key not in kwargs:
            kwargs[key] = value
        else:
            pass

    ### Managing the units ###
    if not "units" in kwargs:
        kwargs["units"] = set_units(qty)
    else:
        kwargs["units"] = pyn.units.Unit(kwargs["units"])
    # PLOTTING #
########################################################################################################################
    ### Making the figure ###
    figure = plt.figure(figsize=tuple(CONFIG["Visualization"]["default_figure_size"]))
    axes = figure.add_subplot(111)

    # - Managing the Extends -# This allows us to set the right ticks and axes.
    numerical_width = float(pyn.units.Unit(kwargs["width"]).in_units(length_units))
    extent = [-numerical_width / 2, numerical_width / 2, -numerical_width / 2, numerical_width / 2]

    ### making the plot ###
    image_array = generate_image_array(snapshot, qty, families=families, **kwargs)
    image = axes.imshow(np.log10(image_array), origin="lower", cmap=kwargs["cmap"], extent=extent)

    ### Managing the colorbar ###
    plt.colorbar(image, label=r"$\mathrm{%s} \;\left[\mathrm{%s}\right]$" % (fancy_qty(qty), kwargs["units"].latex()))
    ### Managing text ###
    # - TITLES -#
    plt.title(r"$t = \mathrm{%s\;%s},\;\;\mathrm{Quantity:\;%s}\;[\mathrm{%s}]$" % (
    np.round(snapshot.properties["time"].in_units(time_units), decimals=2),
    time_units.latex(),
    fancy_qty(qty),
    kwargs["units"].latex()), fontsize=10)
    if title:
        plt.suptitle(title, y=0.93)

    # - AXES LABELS -#
    axes.set_ylabel(r"$y\;\;\left[\mathrm{%s}\right]$" % (pyn.units.Unit(length_units).latex()))
    axes.set_xlabel(r"$x\;\;\left[\mathrm{%s}\right]$" % (pyn.units.Unit(length_units).latex()))


    # Saving
#########################################################################################################################
    if save:
        plt.savefig(end_file)
    else:
        plt.show()

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -----------------------------------------------------   MAIN   --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="FILE",level=30)




    #data = pyn.load(
    #    os.path.join(CONFIG["system"]["directories"]["RAMSES_simulations_directory"], "TestSim", "output_00500"))
    #
    #align_snapshot(data)
    #make_plot(data, "rho",families=["gas"], title="Gas Temperature Map",vmax=1e6, width="5000 kpc",cmap=plt.cm.jet,end_file="/home/ediggins/PyCS/figures/temp.png")

