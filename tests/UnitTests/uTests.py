"""
    Automated test cases for proper running of the system
                Written by: Eliza Diggins

"""
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[2]))
import unittest
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
from PyCS_System.SimulationMangement import SimulationLog
from PyCS_System.SpecConfigs import read_clustep_config,read_batch_config,read_RAMSES_config
from PyCS_Analysis.Images import make_plot
from PyCS_Analysis.Analysis_Utils import align_snapshot
from PyCS_Analysis.Images import __quantities as image_quantities
from PyCS_Analysis.Profiles import __quantities as profile_quantities
from PyCS_Analysis.Profiles import make_profile_plot
import warnings
import pynbody as pyn
import matplotlib.pyplot as plt
from datetime import datetime
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ---------------------------------------------------- setup ------------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
warnings.filterwarnings('ignore')
_location = "uTests"
_filename = pt.Path(__file__).name.replace(".py", "")
_utest_path = pt.Path(__file__).parents[1]
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
set_log(_filename, output_type="FILE", level=10)

# Setting up testlogs file #
report_directory = "Report_%s"%datetime.now().strftime('%m-%d-%Y_%H-%M-%S')

if not os.path.exists(os.path.join(_utest_path,"testlogs",report_directory)):
    pt.Path(os.path.join(_utest_path,"testlogs",report_directory)).mkdir(parents=True)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Tests ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
class TestCore(unittest.TestCase):
    """
    **TestCore**: unit-tests for the ``PyCS_Core`` module.

    ----------------------

    **Tests**:

    *  ``test_config``: Tests that the configuration file can be read.
    *  ``test_logging``: Check that the logging module can be set up.
    """
    cdbg_string = "%sTestCore:" % _dbg_string

    def setUp(self) -> None:
        """
        Set up routine for the unit tests.
        Returns
        -------

        """
        warnings.filterwarnings('ignore')

    def test_config(self):
        """
        Load the configuration file and make sure the output is a dictionary.
        Returns: None
        -------

        """
        fdbg_string = "%stest_config: " % TestCore.cdbg_string
        print("\n%sRunning..." % fdbg_string)
        # Setting up #
        warnings.filterwarnings('ignore')
        try:
            CONFIG = read_config(_configuration_path)
        except:
            raise AssertionError("%sFailed to read configuration file at %s." % (fdbg_string, _configuration_path))

    def test_logging(self):
        """
        Test the ability of the system to open the logging system.
        Returns
        -------

        """
        fdbg_string = "%stest_logging: " % _dbg_string
        print("\n%sRunning..." % fdbg_string)
        try:
            from PyCS_Core.Logging import set_log
            set_log(_filename)
        except:
            raise AssertionError("%sFailed to read configuration file at %s." % (fdbg_string, _configuration_path))


class TestSystem(unittest.TestCase):
    """
    **TestSystem**: Tests the ``PyCS.System`` module for basic loading capacities.

    -----------------------------

    **Tests**:

    * ``test_simlog``: Tests the loading and commands from ``PyCS_System.SimulationManagement.SimulationLog``
    * ``test_RAMSES_config``: Tests the loading of the ramses configuration file.
    * ``test_batch_config``: Same as above, for batch config.
    * ``test_CLUSTEP_config``: Same as above, for clustep config.
    """
    cdbg_string = "%sTestSystem:" % _dbg_string

    def test_simlog(self):
        """

        Returns
        -------

        """
        # Debugging
        # --------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%stest_simlog: " % TestSystem.cdbg_string
        log_print("Running TestSystem.test_simlog...", fdbg_string, "debug")
        print("\n%sRunning..." % fdbg_string)
        # Loading the simulation log
        # --------------------------------------------------------------------------------------------------------------#
        simulationlog = SimulationLog(os.path.join(_utest_path, "testdata", "TestSystem", "test_simlog.log"))

        # CHECKS
        # --------------------------------------------------------------------------------------------------------------#
        # self.named_log
        #  Is it the same length as the actual log? Can we find all of the names?
        #
        log_print("Testing self.named_log()...", fdbg_string, "debug")
        temp_dict = simulationlog.named_log()

        assert len(temp_dict) == len(simulationlog), "%sThe simulation log was not the same length as the named log."
        assert all(name in temp_dict for name in [value["SimulationName"] for value in simulationlog.values()])

        log_print("Passed self.named_log()!", fdbg_string, "debug")
        # --------------------------------------------------------------------------------------------------------------#
        # self._keys_from_name
        #  Is it the same length as the actual log? Can we find all of the names?
        #
        log_print("Testing self._keys_from_name()...", fdbg_string, "debug")
        key = simulationlog._keys_from_name("TestSimulation")

        assert len(key) == 1, "%sFound too many matching keys (%s should be 1)" % (fdbg_string, len(key))
        assert key[
                   0] == "Simulation_1", "%sFailed to find correct key from simulation name 'TestSimulation'... FAILED." % fdbg_string

        log_print("Passed self.keys_from_name()!", fdbg_string, "debug")
        # --------------------------------------------------------------------------------------------------------------#
        # self.named_log
        #  Is it the same length as the actual log? Can we find all of the names?
        #
        log_print("Testing self.named_log()...", fdbg_string, "debug")
        temp_dict = simulationlog.named_log()

        assert len(temp_dict) == len(simulationlog), "%sThe simulation log was not the same length as the named log."
        assert all(name in temp_dict for name in [value["SimulationName"] for value in simulationlog.values()])

        log_print("Passed self.named_log()!", fdbg_string, "debug")
        
    def test_RAMSES_config(self):
        # Debugging
        #--------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%stest_RAMSES_config: " % TestSystem.cdbg_string
        log_print("Running TestSystem.test_RAMSES_config...",fdbg_string,"debug")
        print("\n%sRunning..." % fdbg_string)
        # Attempting to load 
        #--------------------------------------------------------------------------------------------------------------#
        try:
            CNFG = read_RAMSES_config(os.path.join(CONFIG["system"]["directories"]["bin_directory"],"configs","RAMSES_config.ini"))
        except:
            raise AssertionError("%sFailed to read configuration file at %s." % (fdbg_string,os.path.join(CONFIG["system"]["directories"]["bin_directory"],"configs","RAMSES_config.ini")))
        
        # Finishing
        #--------------------------------------------------------------------------------------------------------------#
        log_print("Passed TestSystem.test_RAMSES_config...",fdbg_string,"debug")

    def test_batch_config(self):
        # Debugging
        # --------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%stest_batch_config: " % TestSystem.cdbg_string
        log_print("Running TestSystem.test_batch_config...", fdbg_string, "debug")
        print("\n%sRunning..." % fdbg_string)
        # Attempting to load 
        # --------------------------------------------------------------------------------------------------------------#
        try:
            CNFG = read_batch_config(
                os.path.join(CONFIG["system"]["directories"]["bin_directory"], "configs", "batch_config.ini"))
        except:
            raise AssertionError("%sFailed to read configuration file at %s." % (fdbg_string, os.path.join(
                CONFIG["system"]["directories"]["bin_directory"], "configs", "batch_config.ini")))

        # Finishing
        # --------------------------------------------------------------------------------------------------------------#
        log_print("Passed TestSystem.test_batch_config...", fdbg_string, "debug")

    def test_CLUSTEP_config(self):
        # Debugging
        # --------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%stest_CLUSTEP_config: " % TestSystem.cdbg_string
        log_print("Running TestSystem.test_CLUSTEP_config...", fdbg_string, "debug")
        print("\n%sRunning..." % fdbg_string)
        # Attempting to load 
        # --------------------------------------------------------------------------------------------------------------#
        try:
            CNFG = read_clustep_config(
                os.path.join(CONFIG["system"]["directories"]["bin_directory"], "configs", "CLUSTEP_config.ini"))
        except:
            raise AssertionError("%sFailed to read configuration file at %s." % (fdbg_string, os.path.join(
                CONFIG["system"]["directories"]["bin_directory"], "configs", "CLUSTEP_config.ini")))

        # Finishing
        # --------------------------------------------------------------------------------------------------------------#
        log_print("Passed TestSystem.test_CLUSTEP_config...", fdbg_string, "debug")
    
class TestAnalysis(unittest.TestCase):
    """"""
    cdbg_string = "%sTestAnalysis: "%_dbg_string
    def setUp(self) -> None:
        """
        Set up routine for the unit tests.
        Returns
        -------

        """
        warnings.filterwarnings('ignore')

    def test_images(self):
        # Debugging
        #--------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%stest_images: "%TestAnalysis.cdbg_string
        log_print("Running TestAnalysis.test_images...",fdbg_string,"debug")
        print("%sRunning..."%fdbg_string)

        # Loading the dataset
        #--------------------------------------------------------------------------------------------------------------#
        snapshot = pyn.load(os.path.join(CONFIG["system"]["directories"]["RAMSES_simulations_directory"],"TestSim","output_00500"))
        align_snapshot(snapshot)

        # Setting up the sub-cases
        #--------------------------------------------------------------------------------------------------------------#
        log_print("Performing %s tests: %s"%(len(image_quantities),image_quantities.keys()),fdbg_string,"debug")

        for index,quantity in enumerate(image_quantities):
            # Setting up
            #----------------------------------------------------------------------------------------------------------#
            log_print("Performing test_images on %s..."%quantity,fdbg_string,"debug")
            self.subTest(i=index)
            print("\t%sRunning %s..." % (fdbg_string,quantity))
            output_path = os.path.join(_utest_path,"testlogs",report_directory,"test_images_%s.png"%quantity)

            # Running make image #
            #----------------------------------------------------------------------------------------------------------#
            make_plot(snapshot,quantity,save=True,end_file=output_path,width="5000 kpc",**image_quantities[quantity]["default_settings"])

    def test_profiles(self):
        # Debugging
        # --------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%stest_profiles: " % TestAnalysis.cdbg_string
        log_print("Running TestAnalysis.test_profiles...", fdbg_string, "debug")
        print("%sRunning..." % fdbg_string)

        # Loading the dataset
        # --------------------------------------------------------------------------------------------------------------#
        snapshot = pyn.load(
            os.path.join(CONFIG["system"]["directories"]["RAMSES_simulations_directory"], "TestSim", "output_00500"))
        align_snapshot(snapshot)

        # Setting up the sub-cases
        # --------------------------------------------------------------------------------------------------------------#
        log_print("Performing %s tests: %s" % (len(profile_quantities), profile_quantities.keys()), fdbg_string, "debug")

        for index, quantity in enumerate(profile_quantities):
            # Setting up
            # ----------------------------------------------------------------------------------------------------------#
            log_print("Performing test_profiles on %s..." % quantity, fdbg_string, "debug")
            self.subTest(i=index)
            print("\t%sRunning %s..." % (fdbg_string, quantity))
            output_path = os.path.join(_utest_path, "testlogs", report_directory, "test_profiles_%s.png" % quantity)

            # Running make profile #
            # ----------------------------------------------------------------------------------------------------------#
            make_profile_plot(snapshot,quantity,save=True,end_file=output_path)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Main -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    # --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
    # ------------------------------------------------------ Setup -------------------------------------------------------#
    # --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

    # Running
    unittest.main()
