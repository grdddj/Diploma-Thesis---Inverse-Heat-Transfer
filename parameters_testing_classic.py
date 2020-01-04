"""
This module is testing the impact the change of input parameters
    has to the result (the time and error of the simulation)
"""

import json
import time
import os
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

import heat_transfer_simulation

def _get_average_values_from_results(results):
    """
    Is averaging values from multiple simulations, to account for the fact
        that CPU can have different speed at different times.
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

    averages = defaultdict(dict)

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
                time = simulation_result["time"]
                error = simulation_result["error"]
                averages[parameter][simulation_value]["time"].append(time)
                averages[parameter][simulation_value]["error"].append(error)

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

def show_data_in_jpg(data, file_name):
    """
    Visualises the results in multiple graphs
    Having two y-axes, to improve the visibility of the data
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

        plt.title("Parameters testing - {}".format(parameter))

        plt.grid()

        fig.tight_layout()  # otherwise the right y-label is slightly clipped
        # plt.show()

        file_name_for_picture = "{}-{}.jpg".format(file_name.strip(".json"), parameter)
        plt.savefig(file_name_for_picture)

        plt.clf()


def run_simulation(temperature_plot=None, heat_flux_plot=None,
                   progress_callback=None, queue=None, parameters=None):
    """
    Runs one simulation with inputted parameters and returns the time and
        error of the simulation
    """

    app = heat_transfer_simulation.Trial()

    start_time = time.time()

    app.PrepareSimulation(progress_callback=progress_callback,
                          temperature_plot=temperature_plot,
                          heat_flux_plot=heat_flux_plot,
                          queue=queue,
                          parameters=parameters)
    app.make_sim_step()

    end_time = time.time()
    time_diff = round(end_time - start_time, 3)

    return {
        "time": time_diff,
        "error": app.ErrorNorm
    }

def run_multiple_simulations(parameter, values):
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
        "dt": 1,
        "object_length": 0.01,
        "place_of_interest": 0.0045,
        "number_of_elements": 100,
        "callback_period": 500,
        "robin_alpha": 13.5,
        "theta": 0.5
    }

    # Running the simulation for all the inputted values of the parameter
    for index in range(len(values)):
        current_value = values[index]
        parameters[parameter] = current_value
        print("parameter: {}, value: {}".format(parameter, current_value))

        result = run_simulation(parameters=parameters)
        results[current_value] = result
        print(result)

        # Sleeping some time to "cool off"
        time.sleep(0.1)

    return results

def aggregate_all_tests(testing_scenarios, no_of_repetitions=1):
    """

    """

    results = defaultdict(list)

    # Running the tests multiple times, to account for variable CPU speed
    for _ in range(no_of_repetitions):
        for scenario in testing_scenarios:
            parameter = scenario["parameter"]
            values = scenario["values"]
            result = run_multiple_simulations(parameter=parameter,values=values)

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
    file_name = "{}/{}-{}rep.json".format(directory_for_results, now, no_of_repetitions)
    with open(file_name, 'w') as outfile:
        json.dump(averages, outfile, indent=4)

    # Saving the data to a graph
    show_data_in_jpg(averages, file_name)

if __name__ == '__main__':
    no_of_repetitions = 5
    steps = 200


    # Defining all the scenarios we want to test
    testing_scenarios = [
        # {
        #     "parameter": "number_of_elements",
        #     # "values": list(map(int, np.linspace(10, 1000, steps)))
            # "values": range(1, 100, 1)
        # },
        {
            "parameter": "dt",
            # "values": list(map(int, np.linspace(1, 1000, steps)))
            "values": range(20, 120, 50)
        },
        # {
        #     "parameter": "theta",
        #     "values": np.linspace(0.5, 1.0, steps)
        # }
    ]

    aggregate_all_tests(testing_scenarios=testing_scenarios, no_of_repetitions=no_of_repetitions)
