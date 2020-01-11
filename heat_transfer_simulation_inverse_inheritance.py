"""
This module is serving for running the Inverse simulation.
It can be run separately or from the GUI, in which case
    it will be updating the plot.
"""

import numpy as np
from NumericalInverse_inheritance import InverseSimulation
from experiment_data_handler import Material
from heat_transfer_simulation_utilities import SimulationController


def calculate_error(Sim):
    """
    Function that calculates error value for this simulation
    """

    # TODO: review this, as it might not be correct
    calculated_heatflux = Sim.HeatFlux
    experiment_heatflux = np.interp(Sim.t, Sim.Exp_data.t_data, Sim.Exp_data.q_data)

    # Determining the shorter length, to unify the sizes
    min_length = min(len(calculated_heatflux), len(experiment_heatflux))

    try:
        error = np.sum(abs(calculated_heatflux[:min_length] - experiment_heatflux[:min_length]))/min_length
        return round(error, 3)
    except ValueError:
        # This is raised when the lengths of compared lists are not the same (for some reason)
        return "unknown"


def simulate_from_gui(parameters_from_gui, progress_callback):
    """
    Starts the whole simulation with the inputs from GUI
    """

    return create_and_run_simulation(**parameters_from_gui, progress_callback=progress_callback)


def create_and_run_simulation(parameters, temperature_plot=None, progress_callback=None,
                              heat_flux_plot=None, queue=None, save_results=False):
    """
    Creates a new simulation object, passes it into the controller
        and makes sure the simulation will finish
    """

    my_material = Material(parameters["rho"], parameters["cp"], parameters["lmbd"])
    Sim = InverseSimulation(length=parameters["object_length"],
                            material=my_material,
                            N=parameters["number_of_elements"],
                            theta=parameters["theta"],
                            robin_alpha=parameters["robin_alpha"],
                            dt=parameters["dt"],
                            x0=parameters["place_of_interest"],
                            window_span=parameters["window_span"],
                            tolerance=parameters["tolerance"])

    sim_controller = SimulationController(Sim=Sim,
                                          next_step_func="evaluate_one_inverse_step",
                                          calculate_error_func=calculate_error,
                                          parameters=parameters,
                                          progress_callback=progress_callback,
                                          temperature_plot=temperature_plot,
                                          heat_flux_plot=heat_flux_plot,
                                          queue=queue,
                                          algorithm="Inverse",
                                          time_data_location="t",
                                          quantity_data_location="HeatFlux",
                                          quantity_and_unit="Heat flux [W]",
                                          save_results=save_results)

    result = sim_controller.complete_simulation()
    return result


if __name__ == '__main__':
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

    create_and_run_simulation(parameters)
