"""
This module is defining general infrastructure for the simulations
It can be easily imported and used for any simulation that
    has the same API as defined here (functions prepare_simulation(),
    complete_simulation(), Sim object etc.)
"""

import time


class Callback:
    """
    Class defining the actions that should happen when the simulation
        should share the results with the outside world
    It is also a communication channel between outside world and simulation,
        as it is listening for commands on a shared queue object
    """

    def __init__(self,
                 call_at: float = 500.0,
                 heat_flux_plot=None,
                 temperature_plot=None,
                 queue=None,
                 progress_callback=None) -> None:
        self.call_at = call_at  # how often to be called
        self.last_call = 0.0  # time in which the callback was last called

        # Takes reference of some plot, which it should update, and some queue,
        #   through which the GUI will send information.
        # Also save the progress communication channel to update time in GUI
        self.temperature_plot = temperature_plot
        self.heat_flux_plot = heat_flux_plot
        self.queue = queue
        self.progress_callback = progress_callback

        # Setting the starting simulation state as "running" - this can be
        #   changed only through the queue by input from GUI
        self.simulation_state = "running"

    def __repr__(self) -> str:
        """
        Defining what should be displayed when we print the
            object of this class.
        Very useful for debugging purposes.
        """

        return f"""
            self.call_at: {self.call_at},
            self.temperature_plot: {self.temperature_plot},
            self.heat_flux_plot: {self.heat_flux_plot},
            self.queue: {self.queue},
            self.progress_callback: {self.progress_callback},
            """

    def __call__(self,
                 Sim,
                 force_update: bool = False) -> str:
        """
        Defining what should happend when the callback will be called
        """

        # Doing something when it is time to comunicate with GUI
        if Sim.current_t > self.last_call + self.call_at or force_update:
            # When both the plots are defined, update them
            if self.temperature_plot is not None and self.heat_flux_plot is not None:
                Sim.plot(temperature_plot=self.temperature_plot,
                         heat_flux_plot=self.heat_flux_plot)

            # Updating the time the callback was last called
            self.last_call += self.call_at

        # Getting the connection with GUI and listening for commands
        if self.queue is not None and not self.queue.empty():
            # Getting and parsing the message from shared queue
            # Changing simulation state according that message
            msg = self.queue.get_nowait()
            if msg == "stop":
                self.simulation_state = "stopped"
            elif msg == "pause":
                self.simulation_state = "paused"
            elif msg == "continue":
                self.simulation_state = "running"

        # According to the current state, emit positive or zero
        #   value to give information to the GUI if we are running or not
        if self.progress_callback is not None:
            value_to_emit = 1 if self.simulation_state == "running" else 0
            self.progress_callback.emit(value_to_emit)

        # Returning the current simulation state to be handled by higher function
        return self.simulation_state


class SimulationController:
    """
    Holding variables and defining methods for the simulation
    """

    def __init__(self,
                 Sim,
                 parameters: dict,
                 progress_callback=None,
                 queue=None,
                 temperature_plot=None,
                 heat_flux_plot=None,
                 save_results: bool = False):
        self.Sim = Sim
        self.MyCallBack = Callback(progress_callback=progress_callback,
                                   call_at=parameters["callback_period"],
                                   temperature_plot=temperature_plot,
                                   heat_flux_plot=heat_flux_plot,
                                   queue=queue)
        self.save_results = save_results
        self.progress_callback = progress_callback
        self.temperature_plot = temperature_plot
        self.heat_flux_plot = heat_flux_plot
        self.queue = queue

    def complete_simulation(self) -> dict:
        """
        Running all the simulation steps, if not stopped
        """

        # Calling the evaluating function as long as the simulation has not finished
        while not self.Sim.simulation_has_finished:
            # Processing the callback and getting the simulation state at the same time
            # Then acting accordingly to the current state
            simulation_state = self.MyCallBack(self.Sim)
            if simulation_state == "running":
                # Calling the function that is determining next step
                self.Sim.evaluate_one_step()
            elif simulation_state == "paused":
                # Sleeping for some little time before checking again, to save CPU
                time.sleep(0.1)
            elif simulation_state == "stopped":
                # Breaking out of the loop - finishing simulation
                print("stopping")
                break

        # Calling callback at the very end, to update the plot with complete results
        self.MyCallBack(self.Sim, force_update=True)

        # Invoking whatever action should happen after simulation finishes
        # Passing whole self object, so Simulation has access to all
        #   connections here and can communicate with GUI
        self.Sim.after_simulation_action(self)

        # If wanted to, save the results by a custom function
        if self.save_results:
            self.Sim.save_results()

        return {"error_value": self.Sim.error_norm}
