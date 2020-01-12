"""
This module is testing the impact the change of input parameters
    has to the result (the time and error of the simulation)
"""

import numpy as np

from parameters_testing_utilities import aggregate_all_tests
from heat_transfer_simulation import create_and_run_simulation


def perform_tests():
    """
    Running all the test scenarios defined withing it
    """

    no_of_repetitions = 5
    steps = 200

    # Defining all the scenarios we want to test
    testing_scenarios = [
        {
            "parameter": "number_of_elements",
            # "values": list(map(int, np.linspace(10, 1000, steps)))
            "values": range(1, 100, 50)
        },
        {
            "parameter": "dt",
            # "values": list(map(int, np.linspace(1, 1000, steps)))
            "values": range(20, 120, 50)
        },
        {
            "parameter": "theta",
            # "values": np.linspace(0.5, 1.0, steps)
            "values": np.arange(0.5, 1.0, 0.2)
        }
    ]

    aggregate_all_tests(simulation_func=create_and_run_simulation,
                        testing_scenarios=testing_scenarios,
                        no_of_repetitions=no_of_repetitions,
                        description="classic")


if __name__ == '__main__':
    perform_tests()
