"""
This module is visualising the data from parameter testing

There is a possibility of having x-axis in a logarithmic scale,
    which comes in handy when comparing values that have completely
    different orders
"""

import os
import json
import matplotlib.pyplot as plt

# Defining the file with data, and whether to use logarithmic scale on x-axis
file_name = "1578140846-4rep-inverse.json"
LOGARITHMIC_X_AXIS = True

WORKING_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
directory_for_results = os.path.join(WORKING_DIRECTORY, 'Parameters testing')
file_name_full = os.path.join(directory_for_results, file_name)

def get_data():
    with open(file_name_full, "r") as json_file:
        content = json.load(json_file)
    return content

def show_data():
    data = get_data()

    print(data.keys())

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

        if LOGARITHMIC_X_AXIS:
            plt.xscale('log') # Creating logarithmic scale on x-axis

        plt.grid()

        fig.tight_layout()  # otherwise the right y-label is slightly clipped
        # plt.show()

        file_name_for_picture = "{}-{}-vis.jpg".format(file_name_full.strip(".json"), parameter)
        plt.savefig(file_name_for_picture)

        plt.clf()

if __name__ == '__main__':
    show_data()
