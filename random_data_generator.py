"""
Creating random data for testing purposes.

Transforming random heat flux data into temperature data by running
    forward simulation on them.
"""

import time
import os
import glob
from csv import writer, reader
import numpy as np

from heat_transfer_simulation import create_and_run_simulation
import random_heat_flux_generator


def merge_temp_and_flux_files(temp_file, flux_file):
    """
    Puts together two CSV files with temperature data and with flux data
    """

    temp_time_values = []
    temp_temp_values = []
    with open(temp_file, "r") as csv_file:
        csv_reader = reader(csv_file)
        next(csv_reader, None)
        for row in csv_reader:
            if row and row[0]:
                temp_time_values.append(float(row[0]))
                temp_temp_values.append(float(row[1]))

    flux_time_values = []
    flux_flux_values = []
    flux_ambient_values = []
    with open(flux_file, "r") as csv_file:
        csv_reader = reader(csv_file)
        next(csv_reader, None)
        for row in csv_reader:
            # Disalowing zero time here, as it is not present in temperature file
            if row and float(row[0]):
                flux_time_values.append(float(row[0]))
                flux_flux_values.append(float(row[1]))
                flux_ambient_values.append(float(row[2]))

    # Interpolating temperature data in all the times from flux document
    new_temp = np.interp(flux_time_values, temp_time_values, temp_temp_values)

    new_filename = "aggregated-{}.csv".format(int(time.time()))
    with open(new_filename, "w") as csv_file:
        csv_writer = writer(csv_file)
        headers = ["Time", "HeatFlux", "Temperature", "T_amb"]
        csv_writer.writerow(headers)

        combined = zip(flux_time_values, flux_flux_values, new_temp, flux_ambient_values)

        for row in combined:
            csv_writer.writerow(row)


def run_simulation_and_save_data(data_path: str):
    """
    Runs simulation with general parameters and saves the data
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
        "theta": 0.5,
        "experiment_data_path": data_path
    }

    create_and_run_simulation(parameters=parameters, save_results=True)


if __name__ == '__main__':
    # Generating random heat flux data with a specified function
    random_heat_flux_generator.sinus_data()

    # Searching for the flux CSV file, which will be in the current
    #   directory and will be the most recently modified one
    flux_file = sorted(glob.glob("*.csv"), key=os.path.getmtime, reverse=True)[0]
    print("flux_file", flux_file)

    # Running forward simulation on the generated heat flux data
    run_simulation_and_save_data(flux_file)

    # Searching for the temperature CSV file, which will be in the current
    #   directory and will be the most recently modified one
    temp_file = sorted(glob.glob("*.csv"), key=os.path.getmtime, reverse=True)[0]
    print("temp_file", temp_file)

    # Putting together all the data into one file
    merge_temp_and_flux_files(temp_file=temp_file, flux_file=flux_file)
