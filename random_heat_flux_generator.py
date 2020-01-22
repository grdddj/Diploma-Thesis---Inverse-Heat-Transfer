"""
This module is creating fake data of heat fluxes to have some more
    data to test our inverse simulation on

Kind of data possible:
    - sinus waves
    - square waves
    - completely random (random walk)

    - all with different time durations, different object lengths,
        different point of interest etc.
    - our goal is to have as much diverse scenarios as possible,
        to thoroughly test all the arguments
"""

import random
from csv import writer
import numpy as np
import matplotlib.pyplot as plt


def _save_data(t_data, q_data, T_amb_data: list, file_name: str):
    """
    Saving the data to a specified file
    """

    with open(file_name, "w") as csv_file:
        csv_writer = writer(csv_file)
        headers = ["Time", "HeatFlux", "T_amb"]
        csv_writer.writerow(headers)

        for index in range(np.size(q_data)):
            row = [t_data[index], q_data[index], T_amb_data[index]]
            csv_writer.writerow(row)


def _T_amb_rand_data(size: int, start: float = 21,
                     diff_value: float = 0.05) -> list:
    """
    Returning pseudorandom distribution of ambient temperature
    """

    # Creating a random walk of either adding or subtracting some value
    arr = [start]
    for index in range(1, size):
        new_val = arr[index-1] + random.choice([-diff_value, diff_value])
        arr.append(round(new_val, 2))

    # print(arr)
    return arr


def sinus_data():
    """
    Creating a defined sinus wave
    """

    no_elements = 666
    amplitude = 1000
    cycles = 3
    file_name = "sinus_data.csv"

    t_data = np.arange(0, no_elements, 1)
    sin_periods = np.linspace(0, 2*np.pi*cycles, no_elements)
    q_data = amplitude*np.sin(sin_periods)

    T_amb_data = _T_amb_rand_data(no_elements, 21, 0.05)

    _save_data(t_data, q_data, T_amb_data, file_name)

    plt.plot(t_data, q_data)
    plt.show()


if __name__ == "__main__":
    sinus_data()
