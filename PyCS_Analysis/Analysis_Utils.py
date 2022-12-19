"""

        PyCS Analysis Utils for common use

"""
### Imports ###
# adding the system path to allow us to import the important modules
import os
import sys
import pathlib as pt
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_Core.PyCS_Errors import *
import toml
from datetime import datetime
from colorama import Fore, Back, Style

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------- Multi-Processing Functions ----------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Sub-Functions -----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def align_snapshot(snapshot)->None:
    """
    Aligns a RAMSES snapshot and fixes the units.
    Parameters
    ----------
    snapshot: The snapshot in question.

    Returns: None
    -------

    """
    ##- Intro debugging -##
    fdbg_string = "%salign_snapshot: "%_dbg_string
    log_print("Attempting to align RAMSES snapshot at %s."%snapshot,fdbg_string,"debug")

    ##- Grabbing the Necessary Variables -##
    try:
        boxlength = snapshot.properties["boxsize"]/2 # This is the distance from (0,0,0) of the center of the sim box.
    except KeyError:
        raise IsNotRAMSESError("The simulation is not a RAMSES snapshot.")
    except AttributeError:
        raise IsNotRAMSESError("The simulation is not a RAMSES snapshot.")

    ##- Aligning -##
    try:
        snapshot["pos"] -=boxlength
    except Exception:
        raise SnapshotError("Could not align the snapshot.",snapshot=snapshot) # Raise an error for alignment issues

    ##- Managing Units -##
    snapshot.physical_units() # convert from raw computational units to CSG units.
    log_print("Aligned %s."%snapshot,fdbg_string,"debug")

def smooth_out(snapshot,family):
    """
    Uses the built in functions pyn.sph.smooth and pyn.sph.rho to compute sph values for non-sph families.

    -- THIS SHOULD BE USED CAUTIOUSLY --
    Parameters
    ----------
    snapshot: The snapshot to use.
    family: The family to smooth.

    Returns: None
    -------

    """
    fdbg_string = _dbg_string+"smooth_out: "
    log_print("Smoothing %s in snapshot %s."%(family,snapshot),fdbg_string,"warning")

    ### Grabbing the correct family ###
    fam = None # we need to check for a real family

    for snap_fam in snapshot.families(): # iterate through each snapshot.
        if fam:
            if snap_fam.name == fam.name: # We have a second match for the family
                log_print("Found multiple family matches for %s. Choosing %s over %s..."%(family,snap_fam.name,fam),fdbg_string,"warning")
                fam = snap_fam
        else:
            if snap_fam.name == family: # this is a first pass success
                fam = snap_fam

    if not fam:
        make_error(SnapshotError,fdbg_string,"%s is not a valid family in %s."%(family,snapshot))

    ### Running commands ###
    data[fam]["smooth"] = pyn.sph.smooth(data[fam])
    data[fam]["rho"] = pyn.sph.rho(data[fam])

def get_families(snapshot,family_names:list):
    """
    Checks the snapshot for a matching family name.
    Parameters
    ----------
    snapshot: The snapshot.
    family_names: The string for the family name.

    Returns: The correct actual family.
    -------

    """
    fdbg_string = _dbg_string+"get_family: "
    fams = [] # we need to check for a real family_name

    for snap_fam in snapshot.families(): # iterate through each snapshot.
        if snap_fam.name in family_names:
            fams.append(snap_fam)
        else:
            pass
    return fams
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -----------------------------------------------------   MAIN   --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename,output_type="STDOUT")

    data = pyn.load(os.path.join(CONFIG["system"]["directories"]["RAMSES_simulations_directory"],"TestSim","output_00500"))
    align_snapshot(data)

    import matplotlib.pyplot as plt
    data["smooth"] = pyn.sph.smooth(data)
    pyn.plot.sph.image(data,qty="vx",threaded=False,width="5000 kpc",log=False)
    plt.show()

