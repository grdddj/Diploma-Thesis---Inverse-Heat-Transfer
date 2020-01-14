"""
This unittesting module wants to make sure we accidentally
    do not commit broken version of code that cannot be
    run without changes and debugging
"""

import unittest
import os
import subprocess
import sys

import heat_transfer_simulation as classic_sim
import heat_transfer_simulation_inverse_inheritance as inverse_sim


class TestClassicSimulation(unittest.TestCase):
    def test_error(self):
        """
        Trying to run the simulation and testing the error value1,
            if it is low enough
        More probable cause of failing would be the simulation
            itself throwing an error because of some mistake in code
        """

        parameters = {
            "rho": 7850,
            "cp": 520,
            "lmbd": 50,
            "dt": 1,
            "object_length": 0.01,
            "place_of_interest": 0.0045,
            "number_of_elements": 100,
            "callback_period": 500,
            "robin_alpha": 13.5,
            "theta": 0.5
        }

        result = classic_sim.create_and_run_simulation(parameters)

        # We know that the value should be less than 0.5
        threshold_error_value = 0.5
        self.assertTrue(result["error_value"] < threshold_error_value)


class TestInverseSimulation(unittest.TestCase):
    def test_error(self):
        """
        Trying to run the simulation and testing the error value1,
            if it is low enough
        More probable cause of failing would be the simulation
            itself throwing an error because of some mistake in code
        """

        parameters = {
            "rho": 7850,
            "cp": 520,
            "lmbd": 50,
            "dt": 50,
            "object_length": 0.01,
            "place_of_interest": 0.0045,
            "number_of_elements": 100,
            "callback_period": 500,
            "robin_alpha": 13.5,
            "theta": 0.5,
            "window_span": 2,
            "tolerance": 1e-05
        }

        result = inverse_sim.create_and_run_simulation(parameters)

        # We know that the value should be less than 150
        threshold_error_value = 150
        self.assertTrue(result["error_value"] < threshold_error_value)


class TestMypyAnalysis(unittest.TestCase):
    def test_mypy(self):
        """
        Running the analysis through mypy engine
        If mypy finds any issues, fail the tests

        Needed steps to perform mypy validation:
        - pip install mypy
        - mypy script.py
        - it can happen that it will find "errors", because the
            imported libraries do not incorporate types
        Very nice articles about type-checking in python can be found here:
        - https://realpython.com/python-type-checking/
        - https://medium.com/@ageitgey/learn-how-to-use-static-type-checking-in-python-3-6-in-10-minutes-12c86d72677b

        NOTE: running this test requires mypy (pip install mypy)

        NOTE: some of the reported issues are not real issues,
            and they should be silenced by adding "# type: ignore" comment
            at the end of the line where the "problem" is occurring.
        Every time the problem is spotted, it is necessary to either
            fix it, or silence it by abovementioned comment
        Reason being we want these tests to uncover possible problems
            in the code, so there should be no problems before committing
        """

        WORKING_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

        # Mypy is analysing all the imports as well, so we can only input
        #   the main file to be analysed in case of heat_transfer_gui
        files_to_analyse = [
            "heat_transfer_gui.py",
            "parameters_testing_classic.py",
            "parameters_testing_inverse.py",
            "parameters_testing_utilities.py",
            "parameters_testing_visualisation.py"
        ]

        for file_name in files_to_analyse:
            file_name_full = os.path.join(WORKING_DIRECTORY, file_name)
            print("Analysing {}".format(file_name_full))

            # Running the mypy analysis through the command line
            # NOTE: turns out in python3.6 and below the capture_output
            #   argument is unknown, and therefore it fails here
            if float(sys.version[:3]) < 3.7:
                print("These tests cannot be run, as python3.7 or higher is required")
                continue

            result = subprocess.run(["mypy", file_name_full], capture_output=True, text=True)
            print(result.stdout)

            # We will receive a result message, and we want to see
            #   certain success message inside to know validation is alright
            success_text = "no issues found"
            self.assertTrue(success_text in result.stdout)


if __name__ == '__main__':
    unittest.main()
