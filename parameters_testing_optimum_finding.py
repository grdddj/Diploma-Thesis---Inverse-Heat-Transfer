"""
This module is finding out the optimal value for testing parameters

We are identifying the values that yield the smallest product
    of multiplying the simulation time with error margin
"""

import os
import json

directory_for_results = 'Parameters testing'
file_name = "1578140846-4rep-inverse.json"


def get_data(file_name:str ) -> dict:
    """
    Simply getting data from specified json file name and returning them
        in the form of a python dictionary
    """

    with open(file_name, "r") as json_file:
        content = json.load(json_file)
    return content


def analyse_data(data: dict) -> list:
    """
    Analysing the inputted data and returning the optimal values
    """

    optimal_values = {}

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

        # Seeing which key has the lowest multiplication of time and error
        products = []
        for time, error in zip(time_values, error_values):
            product = round(time * error, 4)
            products.append(product)

        min_value = min(products)
        min_index = products.index(min_value)
        optimal_value = keys[min_index]

        optimal_values[parameter] = optimal_value

    return optimal_values


if __name__ == '__main__':
    WORKING_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
    directory_for_results_full = os.path.join(WORKING_DIRECTORY, directory_for_results)
    file_name_full = os.path.join(directory_for_results_full, file_name)

    data = get_data(file_name_full)
    result = analyse_data(data)
    print(result)
