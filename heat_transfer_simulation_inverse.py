"""
This module is serving for running the Inverse simulation.
It can be run separately or from the GUI, in which case
    it will be updating the plot.
"""

from NumericalInverse import InverseSimulation
from experiment_data_handler import Material
from heat_transfer_simulation_utilities import SimulationController


def simulate_from_gui(parameters_from_gui: dict,
                      progress_callback) -> dict:
    """
    Starts the whole simulation with the inputs from GUI
    """

    return create_and_run_simulation(progress_callback=progress_callback,
                                     **parameters_from_gui)


def create_and_run_simulation(parameters,
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
    Sim = InverseSimulation(length=parameters["object_length"],
                            material=my_material,
                            N=parameters["number_of_elements"],
                            theta=parameters["theta"],
                            robin_alpha=parameters["robin_alpha"],
                            dt=parameters["dt"],
                            x0=parameters["place_of_interest"],
                            window_span=parameters["window_span"],
                            q_init=parameters["q_init"],
                            init_q_adjustment=parameters["init_q_adjustment"],
                            adjusting_value=parameters["adjusting_value"],
                            tolerance=parameters["tolerance"],
                            experiment_data_path=parameters["experiment_data_path"])

    sim_controller = SimulationController(Sim=Sim,
                                          parameters=parameters,
                                          progress_callback=progress_callback,
                                          temperature_plot=temperature_plot,
                                          heat_flux_plot=heat_flux_plot,
                                          queue=queue,
                                          save_results=save_results)

    result = sim_controller.complete_simulation()
    return result


if __name__ == '__main__':
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
        "window_span": 6,
        "tolerance": 1e-04,
        "q_init": 0,
        "init_q_adjustment": 10,
        "adjusting_value": -0.7,
        "experiment_data_path": "DATA.csv"
    }

    create_and_run_simulation(parameters)
