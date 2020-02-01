"""
This module is resposible for thorough testing of parameters
    during inverse simulation.
It is running simulation for all possible combinations
    of multiple parameters and saving results into CSV file.
"""

import time
from csv import writer
import os
import itertools
from typing import Callable

import numpy as np  # type: ignore

from heat_transfer_simulation_inverse import create_and_run_simulation


def process_results(file_name, parameters_dict, error, time):
    """
    Saves the current result into a defined CSV file
    """

    # Aggregating all the changed parameters and result
    with open(file_name, "a") as csv_file:
        csv_writer = writer(csv_file)

        row_to_write = []
        for _, value in parameters_dict.items():
            row_to_write.append(value)

        row_to_write.append(error)
        row_to_write.append(time)

        csv_writer.writerow(row_to_write)


def run_simulation_with_parameters(simulation_func: Callable,
                                   parameters_dict: dict,
                                   file_name: str) -> None:
    """
    Is running simulation with some changed parameters
    """

    # Default parameters, into which the new parameter will be injected,
    #   but the rest will stay the same
    parameters = {
        "rho": 7850,
        "cp": 520,
        "lmbd": 50,
        "dt": 3,
        "object_length": 0.01,
        "place_of_interest": 0.0045,
        "number_of_elements": 100,
        "callback_period": 500,
        "robin_alpha": 13.5,
        "theta": 0.5,
        "window_span": 2,
        "tolerance": 1e-05,
        "q_init": 0,
        "init_q_adjustment": 20,
        "adjusting_value": -0.7,
        "experiment_data_path": "DATA.csv"
    }

    # Assigning all the parameters that should change
    for param, value in parameters_dict.items():
        parameters[param] = value

    start_time = time.perf_counter()

    result = simulation_func(parameters=parameters)

    end_time = time.perf_counter()
    time_diff = round(end_time - start_time, 3)

    process_results(file_name, parameters_dict, result["error_value"], time_diff)


def aggregate_all_tests(simulation_func: Callable,
                        testing_scenarios: list,
                        file_name: str):
    """
    Runs simulations with all possible combinations of inputted scenarios
    """

    # Aggregating all scenarios into lists, from which we can
    #   extract all permutations (possible combination of those)
    all_variable_param_values = []
    param_names = []
    for scenario in testing_scenarios:
        all_variable_param_values.append(scenario["values"])
        param_names.append(scenario["parameter"])

    # Creating a CSV file for the results and populating it with headers
    with open(file_name, "w") as csv_file:
        csv_writer = writer(csv_file)
        headers = param_names[:]
        headers.append("error")
        headers.append("time")
        csv_writer.writerow(headers)

    all_permutations = list(itertools.product(*all_variable_param_values))

    # Constructing right parameters and calling simulation for all the
    #   possible situations
    for permutation_values in all_permutations:
        parameters_dict = {}
        for index, value in enumerate(permutation_values):
            parameters_dict[param_names[index]] = value
        print(parameters_dict)
        run_simulation_with_parameters(simulation_func=simulation_func,
                                       parameters_dict=parameters_dict,
                                       file_name=file_name)


def perform_tests():
    """
    Running all the test scenarios defined withing it
    """

    # Defining all the scenarios we want to test
    testing_scenarios = [
        {
            "parameter": "number_of_elements",
            "values": range(5, 100, 5)
        },
        {
            "parameter": "dt",
            # "values": list(map(int, np.linspace(1, 1000, steps)))
            "values": range(1, 50, 2)
        },
        {
            "parameter": "window_span",
            "values": range(2, 20)
        },
    ]

    file_name = "{}.csv".format(int(time.time()))
    WORKING_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
    file_name = os.path.join(WORKING_DIRECTORY, file_name)

    aggregate_all_tests(simulation_func=create_and_run_simulation,
                        testing_scenarios=testing_scenarios,
                        file_name=file_name)


if __name__ == '__main__':
    perform_tests()
