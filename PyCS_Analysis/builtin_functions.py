"""

    Useful pre-defined functions for analysis
        Written by: Eliza Diggins
"""
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import numpy as np
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.PyCS_Errors import *
from scipy.integrate import solve_ivp
import pynbody as pyn
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# - Fixed constants -#
mass_fraction = 0.6  # The standard mass fraction. This value is from Schneider (Extragalactic astronomy)
boltzmann_constant = 1.381e-23 * pyn.units.Unit("J K^-1")
G = 6.675e-11 * pyn.units.Unit("N m^2 kg^-2")
m_p = 1.672621911e-27 * pyn.units.Unit("kg")
rho_critical = 8.5e-27 * pyn.units.Unit("kg m^-3")  # universe critical density.

# - smoothing kernel -#
smth_kern = lambda x: (1 / np.sqrt(2 * np.pi)) * np.exp((-(x) ** 2) / 5)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ---------------------------------------------------- Sub-Functions ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def smooth_func(function, bandwidth=10):
    return lambda r: np.convolve(function(r), np.ones(bandwidth) / bandwidth, mode="same")


def find_rx(snapshot, p=500 * rho_critical):
    """
    Determines the maximal radius of the ``snapshot`` at which the total density is >= ``p``.
    Parameters
    ----------
    snapshot: The snapshot to analyze.
    p: The density to look for.

    Returns: The radius of the specified density.
    -------

    """
    # Intro debugging
    ####################################################################################################################
    fdbg_string = "%sfind_rx: "
    log_print("Looking for %s radius in %s." % (p, snapshot), fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    # - generating the necessary profile -#
    profile = pyn.analysis.profile.Profile(snapshot, nbins=1000, ndim=3)

    rbins, density = profile["rbins"], profile["density"]

    # Computing
    ####################################################################################################################
    rbins = rbins[np.where(density >= p)]
    return np.amax(rbins)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Profiles -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -
# These functions are all Lambda-generators, i.e. they produce lambda functions based on the inputs.
# -
def hydrostatic_mass(subsnap,
                     mu: float = mass_fraction,
                     independent_unit=CONFIG["units"]["default_length_unit"],
                     dependent_unit=CONFIG["units"]["default_mass_unit"],
                     **kwargs):
    """
    Constructs the mass profile base on the hydrostatic assumption and spherical symmetry.

    M(<r) = ((k*T*r^2)/(mu*m_p*G))*[(dln(rho)/dr) + (dln(T)/dr)]

    Parameters
    ----------
    kwargs: additional kwargs to pass to pyn.analysis.profile.Profile()
    subsnap: the Pynbody snapshot or sub-snapshot to analyze. **Must be pre-aligned and centered**
    mu: The ICM mass fraction.
    independent_unit: The length unit to use as input. Must match the data length unit.
    dependent_unit: The output unit to use as the mass unit. Must match the data mass unit.

    Returns: Lambda function - M(<r) - in ``dependent_units`` = Lf(r - in ``independent_units``)
    -------

    """
    # Intro debugging
    ####################################################################################################################
    fdbg_string = "%shydrostatic_mass: " % _dbg_string
    log_print("Constructing a hydrostatic mass lambda for %s." % subsnap, fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    # - managing unit types -#
    if isinstance(independent_unit, str):
        independent_unit = pyn.units.Unit(independent_unit)
    if isinstance(dependent_unit, str):
        dependent_unit = pyn.units.Unit(dependent_unit)

    # Collecting necessary datasets
    ####################################################################################################################
    try:
        # - generating the profile -#
        gas_profile = pyn.analysis.profile.Profile(subsnap.g, ndim=3, **kwargs)

        # - extracting important arrays
        temp_g = gas_profile["temp"].in_units("K")
        rho_g = gas_profile["rho"].in_units("Msol kpc^-3")
        dtemp_g = gas_profile["d_temp"].in_units("K %s^-1" % str(independent_unit))
        drho_g = gas_profile["d_rho"].in_units("Msol kpc^-3 %s^-1" % str(independent_unit))
        r_vals = gas_profile["rbins"].in_units(independent_unit)
    except Exception:
        make_error(SnapshotError, fdbg_string, "Failed to extract a gas profile from %s." % subsnap)
        return None  # IDE calming

    # Generate the r-lambda
    ####################################################################################################################
    r_index = lambda r: np.piecewise(r,
                                     [(r >= r_vals[i]) & (r < r_vals[i + 1]) for i, rs in enumerate(r_vals[:-1])] + [
                                         (r >= r_vals[-1])],
                                     [int(i) for i in
                                      list(range(len(r_vals)))])  # generates the r-indexing array function
    # Generating the lambda-function
    ####################################################################################################################
    # - Coercing units -#
    k_temp = boltzmann_constant.in_units("%s m^2 s^-2 K^-1" % str(dependent_unit))  # convert k to M m^2/s^2
    G_temp = G.in_units("m^2 s^-2 kg^-1 %s" % str(independent_unit))
    m_p_temp = m_p.in_units("kg")

    # - constructing the lambda function -#
    hydro_func = lambda r: -1 * ((k_temp) / (mu * G_temp * m_p_temp)) * (
            (temp_g[r_index(r).astype("int32")]) * (r_vals[r_index(r).astype("int32")] ** 2)) * (
                                   ((1 / rho_g[r_index(r).astype("int32")]) * (drho_g[r_index(r).astype("int32")]))
                                   + ((1 / temp_g[r_index(r).astype("int32")]) * (
                               dtemp_g[r_index(r).astype("int32")])))

    return smooth_func(hydro_func)


def dehnen_profile(mass,
                   gamma,
                   a,
                   independent_unit=CONFIG["units"]["default_length_unit"],
                   dependent_unit=CONFIG["units"]["default_density_unit"]):
    """
    Returns a lambda function for a Dehnen_profile (Dehnen 1993) with the specified gamma, a, and mass.
    Parameters
    ----------
    independent_unit: the length unit to use.
    dependent_unit: the density unit to use.
    mass: the total mass.
    gamma: the gamma parameter.
    a: the scale length

    Returns: lambda function
    -------

    """
    # intro debugging
    ####################################################################################################################
    fdbg_string = "%sdehnen_profile: " % _dbg_string
    log_print("Generating a dehnen profile with parameters (%s,%s,%s)" % (mass, gamma, a), fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    # - assigning units as necessary -#
    if not isinstance(mass, pyn.units.CompositeUnit):
        mass = mass * pyn.units.Unit(CONFIG["units"]["default_mass_unit"])

    if not isinstance(a, pyn.units.CompositeUnit):
        a = a * pyn.units.Unit(CONFIG["units"]["default_length_unit"])

    independent_unit, dependent_unit = (pyn.units.Unit(unit) if isinstance(unit, str) else unit for unit in
                                        [independent_unit, dependent_unit])

    # Unit Coercion
    ####################################################################################################################
    # - Setting core parameters to managable units -#
    # mass now takes the default unit and a is coverted to the input.
    mass, a = mass.in_units(CONFIG["units"]["default_mass_unit"]), a.in_units(independent_unit)

    # mass conversion fact to multiply by in order to get the intended values
    conversion_factor = (pyn.units.Unit(CONFIG["units"]["default_mass_unit"]) / independent_unit ** 3).ratio(
        dependent_unit)

    # generating the lambda function
    ####################################################################################################################
    return lambda r: (((3 - gamma) * mass) / (4 * np.pi)) * (
            a / ((r ** gamma) * ((r + a) ** (4 - gamma)))) * conversion_factor


def dehnen_mass_profile(mass,
                        gamma,
                        a,
                        independent_unit=CONFIG["units"]["default_length_unit"],
                        dependent_unit=CONFIG["units"]["default_mass_unit"]):
    """
    Returns a lambda function for a Dehnen_profile (Dehnen 1993) integrated with the specified gamma, a, and mass.
    Parameters
    ----------
    independent_unit: the length unit to use.
    dependent_unit: the density unit to use.
    mass: the total mass.
    gamma: the gamma parameter.
    a: the scale length

    Returns: lambda function
    -------

    """
    # intro debugging
    ####################################################################################################################
    fdbg_string = "%sdehnen_mas_profile: " % _dbg_string
    log_print("Generating a dehnen profile with parameters (%s,%s,%s)" % (mass, gamma, a), fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    # - assigning units as necessary -#
    if not isinstance(mass, pyn.units.CompositeUnit):
        mass = mass * pyn.units.Unit(CONFIG["units"]["default_mass_unit"])

    if not isinstance(a, pyn.units.CompositeUnit):
        a = a * pyn.units.Unit(CONFIG["units"]["default_length_unit"])

    independent_unit, dependent_unit = (pyn.units.Unit(unit) if isinstance(unit, str) else unit for unit in
                                        [independent_unit, dependent_unit])

    # Unit Coercion
    ####################################################################################################################
    # - Setting core parameters to managable units -#
    # mass now takes the default unit and a is coverted to the input.
    mass, a = mass.in_units(CONFIG["units"]["default_mass_unit"]), a.in_units(independent_unit)

    # mass conversion fact to multiply by in order to get the intended values
    conversion_factor = (pyn.units.Unit(CONFIG["units"]["default_mass_unit"])).ratio(dependent_unit)

    # generating the lambda function
    ####################################################################################################################
    return lambda r: conversion_factor * mass * ((r) / (r + a)) ** (3 - gamma)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Mathematics --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# - These are all functions related to useful analysis.
def generate_xray_emissivity(snapshot, emin, emax):
    """
    Generates the x-ray emissivity for the cluster based on the given snapshot and the specified emin, emax.

    We use the formula

    e_ff = n_e^2 * G(E,T) * (kT)^(-1/2) exp(-E/kT)

    Which, after subsequent calculations simplifies to

    rho_g^2 * (kT)^(1/2) * (0.9/(1.252 m_p)^2) * integral from E_min/kT to E_max/kT x^-0.3 * exp(-x).

    Parameters
    ----------
    snapshot: The snapshot on which to compute the value.
    emin: The minimum energy for the computation.
    emax: The maximum energy for the computation.

    Returns
    -------

    """
    # Intro debugging
    ####################################################################################################################
    fdbg_string = "%sgenerate_xray_emissivity: "
    log_print("Generating x-ray emissivity map for %s." % snapshot, fdbg_string, "debug")

    # SETUP and TYPE COERCION
    ####################################################################################################################
    # - Forcing corrected energy units -#
    if isinstance(emin, pyn.units.CompositeUnit):  # These are united.
        emin = emin.in_units("keV")

    if isinstance(emax, pyn.units.CompositeUnit):
        emax = emax.in_units("keV")

    for e_arg in [emax, emin]:
        assert isinstance(e_arg, (
        float, int)), "One or both of the energy arguments could not be coerced into a float (%s)." % e_arg

    # Defining subscope integral
    ####################################################################################################################
    def __subscope_integral(T):
        # REQUIRE T UNITLESS in K.
        range_space = np.linspace(emin / (8.617e-8 * T), emax / (8.617e-8 * T), 100)
        integrand = range_space ^ (-0.3) * np.exp(range_space)

        return np.trapz(integrand, x=range_space)

    # Generating the field
    ####################################################################################################################
    #TODO: IN PROGRESS, NOT FINISHED!
def get_collision_parameters(masses,
                             impact_parameter,
                             initial_velocity,
                             initial_separation,
                             events=None,
                             time_length=10 * pyn.units.Unit("Gyr"),
                             max_step=1 * pyn.units.Unit("Myr")):
    """
    Generates the collision parameter state that we expect from the cluster interaction.
    Parameters
    ----------
    masses: the masses of the two clusters. If not specified, assumed in Msol.
    impact_parameter: The impact parameter (kpc by default)
    initial_velocity: the initial velocity (km/s by default)
    initial_separation: The initial x separation of the two clusters.
    eta: The distance at which to discriminate.

    Returns
    -------

    """
    # initial debug
    ####################################################################################################################
    fdbg_string = "%sget_collision_parameters: " % _dbg_string
    log_print("Getting collision parameters for collision with (m=%s,b=%s,v=%s,dx=%s)" % (masses,
                                                                                          impact_parameter,
                                                                                          initial_velocity,
                                                                                          initial_separation),
              fdbg_string,
              "debug")

    # Managing units
    ####################################################################################################################
    # - dealing with masses -#
    for id, mass in enumerate(masses):
        if not isinstance(mass, (pyn.units.CompositeUnit, pyn.array.SimArray)):
            masses[id] = mass * pyn.units.Unit(CONFIG["units"]["default_mass_unit"])

    # - dealing with others -#
    params = [impact_parameter, initial_velocity, initial_separation]
    for item, unit in zip([0, 1, 2], [CONFIG["units"]["default_length_unit"],
                                      CONFIG["units"]["default_velocity_unit"],
                                      CONFIG["units"]["default_length_unit"]]):
        if not isinstance(params[item], pyn.units.CompositeUnit):
            # This item doesn't have units yet.
            params[item] = params[item] * pyn.units.Unit(unit)
        else:
            pass

    # Generating initial data
    ####################################################################################################################
    # - coercing units -#
    # This is all designed for dr/dt in km/s and r in km.
    G_temp = G.in_units("km^3 Msol^-1 s^-2")  # correcting G units
    mass = sum([m.in_units("Msol") for m in masses])
    b, v_0, x_0 = params[0].in_units("km"), params[1].in_units("km s^-1"), params[2].in_units("km")

    # - Making IC computations -#
    r_0 = np.sqrt(b ** 2 + x_0 ** 2)  # initial total separation.
    dr_0 = v_0 * (x_0 / r_0)  # ---> this is v_0 cos(theta).
    phi_0 = np.arctan(b / x_0)

    # Solving
    ####################################################################################################################
    function = lambda t, r: [r[1], -((G_temp * mass) / (r[0] ** 2)) + (b * v_0) ** 2 / (r[0] ** 3),
                             (b * v_0) / (r[0] ** 2)]
    solved_data = solve_ivp(function, (0, time_length.in_units("s")), [r_0, dr_0, phi_0], events=events,
                            max_step=max_step.in_units("s"), vectorized=True)
    # post_processing
    ####################################################################################################################
    solved_data.y[0] = solved_data.y[0] * pyn.units.Unit("km").ratio(pyn.units.Unit("kpc"))
    solved_data.t = solved_data.t * pyn.units.Unit("s").ratio(pyn.units.Unit("Gyr"))
    # - Fixing the units of the events -#
    for id, event in enumerate(solved_data.t_events):
        if len(event) != 0:
            solved_data.t_events[id] = [ev * pyn.units.Unit("s").ratio(pyn.units.Unit("Gyr")) for ev in event]

    for id, event in enumerate(solved_data.y_events):  # this iterates through each event function
        # we fix the 0th id of all
        if len(event) != 0:
            solved_data.y_events[id][:, 0] = [event_case[0] * pyn.units.Unit("km").ratio(pyn.units.Unit("kpc")) for
                                              event_case in event]

    # creating the com information
    solved_data.com_y_events = []
    for id, event in enumerate(solved_data.y_events):
        if len(event) != 0:
            solved_data.com_y_events.append(
                np.array([[(-masses[0].in_units("Msol") / mass) * solved_data.y_events[id][j][0],
                           (masses[1].in_units("Msol") / mass) * solved_data.y_events[id][j][0]] for j in
                          range(len(event))]))
        else:
            solved_data.com_y_events.append(np.array([]))

    # - adding COM -#
    solved_data.com_y = [(-masses[0].in_units("Msol") / mass) * solved_data.y[0],
                         (masses[1].in_units("Msol") / mass) * solved_data.y[0]]
    return solved_data


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    set_log(_filename, output_type="STDOUT")
    data = get_collision_parameters([1e15, 1e15], 2, -1000, 6,
                                    events=[lambda t, y: y[0] - float(500 * pyn.units.Unit("kpc").in_units("km")),
                                            lambda t, y: y[0] - float(1000 * pyn.units.Unit("kpc").in_units("km"))])
    print(data.t_events, data.com_y_events, data.y_events)
    plt.plot(data.com_y[0] * np.cos(data.y[2]), data.com_y[0] * np.sin(data.y[2]))
    plt.plot(data.com_y[1] * np.cos(data.y[2]), data.com_y[1] * np.sin(data.y[2]))
    for y_event, com_event, c in zip(data.y_events, data.com_y_events, ["red", "green"]):
        plt.scatter(com_event[:][0] * np.cos(y_event[0, 2]), com_event[:][0] * np.sin(y_event[0, 2]), color=c)
        plt.scatter(com_event[:][1] * np.cos(y_event[1, 2]), com_event[:][1] * np.sin(y_event[1, 2]), color=c)
    plt.show()
    plt.plot(data.t, data.y[1])
    plt.plot(data.t, data.y[2])

    plt.show()
