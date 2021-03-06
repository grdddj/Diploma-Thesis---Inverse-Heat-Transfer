"""
This module provides common functionality for the parameters testing
"""

import json
import time
import os
from collections import defaultdict
from typing import Callable, Dict, Any
import matplotlib.pyplot as plt  # type: ignore


def _get_average_values_from_results(results: dict) -> dict:
    """
    Is averaging values from multiple simulations, to account for the fact
        that CPU can have different speed at different times
    In order to avoid problems with converting to json later, we are
        stringifying all the keys

    EXAMPLE:
    {
        "number_of_elements": [
            {
                "10": {
                    "time": 0.553,
                    "error": 0.557
                },
                "30": {
                    "time": 0.647,
                    "error": 0.464
                }
            },
            {
                "10": {
                    "time": 0.521,
                    "error": 0.557
                },
                "30": {
                    "time": 0.786,
                    "error": 0.464
                }
            }
        ]
    }

    RESULTS IN

    {
        "number_of_elements": {
            "10": {
                "time": 0.537,
                "error": 0.557
            },
            "30": {
                "time": 0.717,
                "error": 0.464
            }
        }
    }
    """

    averages: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)

    # Filling the averages with the empty data, to be filled later
    for parameter, simulation_list in results.items():
        simulation_values = simulation_list[0].keys()
        for value in simulation_values:
            value = str(value)
            averages[parameter][value] = {"time": [], "error": []}

    # Filling the averages with all the available data
    for parameter, simulation_list in results.items():
        for simulation in simulation_list:
            for simulation_value, simulation_result in simulation.items():
                simulation_value = str(simulation_value)
                sim_time = simulation_result["time"]
                sim_error = simulation_result["error"]
                averages[parameter][simulation_value]["time"].append(sim_time)
                averages[parameter][simulation_value]["error"].append(sim_error)

    print(80*"*")
    print(averages)

    # Aggregating all the values into one average ones
    for parameter, values_dict in averages.items():
        for value, key_dict in values_dict.items():
            value = str(value)
            for key, list_of_measurements in key_dict.items():
                average_value = round(sum(list_of_measurements) / len(list_of_measurements), 3)
                averages[parameter][value][key] = average_value

    return averages


def _show_data_in_jpg(data: dict,
                      file_name: str,
                      description: str = "classic") -> None:
    """
    Visualises the results in multiple graphs
    """

    for parameter in data.keys():
        elem = data[parameter]
        print("len - {}".format(len(elem.keys())))

        keys = []
        time_values = []
        error_values = []

        for key, value in elem.items():
            keys.append(float(key))
            time_values.append(float(value["time"]))
            error_values.append(float(value["error"]))

        fig, ax1 = plt.subplots()

        color = 'tab:blue'
        ax1.set_xlabel(parameter)
        ax1.set_ylabel('time [s]', color=color)
        ax1.plot(keys, time_values, color=color)
        ax1.tick_params(axis='y', labelcolor=color)

        ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

        color = 'tab:red'
        ax2.set_ylabel('error [-]', color=color)  # we already handled the x-label with ax1
        ax2.plot(keys, error_values, color=color)
        ax2.tick_params(axis='y', labelcolor=color)

        plt.title("Parameters testing {} - {}".format(description, parameter))

        plt.grid()

        fig.tight_layout()  # otherwise the right y-label is slightly clipped
        # plt.show()

        file_name_for_picture = "{}-{}.png".format(file_name.strip(".json"),
                                                   parameter)
        plt.savefig(file_name_for_picture)

        plt.clf()


def _run_simulation(simulation_func: Callable,
                    parameters: dict,
                    temperature_plot=None,
                    heat_flux_plot=None,
                    progress_callback=None,
                    queue=None) -> dict:
    """
    Runs one simulation with inputted parameters and returns the time and
        error of the simulation
    """

    start_time = time.perf_counter()

    result = simulation_func(parameters=parameters)

    end_time = time.perf_counter()
    time_diff = round(end_time - start_time, 3)

    return {
        "time": time_diff,
        "error": result["error_value"]
    }


def _run_multiple_simulations(simulation_func: Callable,
                              parameter: str,
                              values: list) -> dict:
    """
    Runs simulations multiple times for all inputted values, that are
        meant to modify certain parameter, and should change the results
    """

    results = {}

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
        "window_span": 4,
        "tolerance": 1e-05,
        "init_q_adjustment": 20,
        "adjusting_value": -0.7,
        "experiment_data_path": "DATA.csv"
    }

    # Running the simulation for all the inputted values of the parameter
    for value in values:
        parameters[parameter] = value
        print("parameter: {}, value: {}".format(parameter, value))

        result = _run_simulation(simulation_func=simulation_func,
                                 parameters=parameters)
        results[value] = result
        print(result)

        # Sleeping some time to "cool off"
        time.sleep(0.1)

    return results


def aggregate_all_tests(simulation_func: Callable,
                        testing_scenarios: list,
                        no_of_repetitions: int = 1,
                        description: str = "classic"):
    """
    Running all the testing scenarios specified number of times
    """

    results: Dict[str, list] = defaultdict(list)

    # Running the tests multiple times, to account for variable CPU speed
    for _ in range(no_of_repetitions):
        for scenario in testing_scenarios:
            parameter = scenario["parameter"]
            values = scenario["values"]
            result = _run_multiple_simulations(simulation_func=simulation_func,
                                               parameter=parameter,
                                               values=values)

            results[parameter].append(result)

            # Sleeping some time to "cool off"
            time.sleep(0.5)

    averages = _get_average_values_from_results(results)

    # Saving the results to a json file
    now = int(time.time())
    WORKING_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
    directory_for_results = os.path.join(WORKING_DIRECTORY, 'Parameters testing')
    if not os.path.isdir(directory_for_results):
        os.mkdir(directory_for_results)
    file_name = "{}/{}-{}rep-{}.json".format(directory_for_results, now,
                                             no_of_repetitions, description)
    with open(file_name, 'w') as outfile:
        json.dump(averages, outfile, indent=4)

    # Saving the data to a graph
    _show_data_in_jpg(data=averages, file_name=file_name, description=description)
