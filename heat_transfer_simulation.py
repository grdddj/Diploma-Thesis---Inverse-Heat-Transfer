"""
This module is serving for running the Classic simulation.
It can be run separately or from the GUI, in which case
    it will be updating the plot.
"""

import numpy as np  # type: ignore
from NumericalForward import Simulation
from experiment_data_handler import Material
from heat_transfer_simulation_utilities import SimulationController


def calculate_error(Sim) -> float:
    """
    Function that calculates error value for this simulation
    """

    error = np.sum(abs(Sim.T_x0 - Sim.T_data))/len(Sim.t[1:])
    return round(error, 3)


def simulate_from_gui(parameters_from_gui: dict) -> dict:
    """
    Starts the whole simulation with the inputs from GUI
    """

    return create_and_run_simulation(**parameters_from_gui)


def create_and_run_simulation(parameters: dict,
                              temperature_plot=None,
                              progress_callback=None,
                              heat_flux_plot=None,
                              queue=None,
                              save_results: bool = False) -> dict:
    """
    Creates a new simulation object, passes it into the controller
        and makes sure the simulation will finish
    """

    my_material = Material(parameters["rho"], parameters["cp"], parameters["lmbd"])
    Sim = Simulation(length=parameters["object_length"],
                     material=my_material,
                     N=parameters["number_of_elements"],
                     theta=parameters["theta"],
                     robin_alpha=parameters["robin_alpha"],
                     dt=parameters["dt"],
                     x0=parameters["place_of_interest"])

    sim_controller = SimulationController(Sim=Sim,
                                          next_step_func="evaluate_one_step",
                                          calculate_error_func=calculate_error,
                                          parameters=parameters,
                                          progress_callback=progress_callback,
                                          temperature_plot=temperature_plot,
                                          heat_flux_plot=heat_flux_plot,
                                          queue=queue,
                                          algorithm="Classic",
                                          time_data_location="t",
                                          quantity_data_location="T_x0",
                                          quantity_and_unit="Temperature [C]",
                                          save_results=save_results,
                                          not_replot_heatflux=True)

    result = sim_controller.complete_simulation()
    return result


if __name__ == '__main__':
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

    create_and_run_simulation(parameters)
