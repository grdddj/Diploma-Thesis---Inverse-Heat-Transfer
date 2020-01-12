"""
This module is defining general infrastructure for the simulations
It can be easily imported and used for any simulation that
    has the same API as defined here (functions prepare_simulation(),
    complete_simulation(), Sim object etc.)
"""

import csv
import time


class Callback:
    """
    Class defining the actions that should happen when the simulation
        should share the results with the outside world
    """

    def __init__(self, call_at=500.0, heat_flux_plot=None,
                 temperature_plot=None, queue=None, progress_callback=None,
                 not_replot_heatflux=False):
        self.call_at = call_at  # how often to be called
        self.last_call = 0  # time in which the callback was last called

        # Takes reference of some plot, which it should update, and some queue,
        #   through which the GUI will send information.
        # Also save the progress communication channel to update time in GUI
        self.temperature_plot = temperature_plot
        self.heat_flux_plot = heat_flux_plot
        self.queue = queue
        self.progress_callback = progress_callback

        # Soemtimes do not want to waste time by plotting the same heat_flux values
        #   over and over, so we do that only once, and flag it to be done
        self.not_replot_heatflux = not_replot_heatflux
        self.heat_flux_already_plotted = False

        # Setting the starting simulation state as "running" - this can be
        #   changed only through the queue by input from GUI
        self.simulation_state = "running"

    def __repr__(self):
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
            self.not_replot_heatflux: {self.not_replot_heatflux},
            """

    def __call__(self, Sim, force_update=False):
        """
        Defining what should happend when the callback will be called
        """

        # Update the time calculation is in progress
        # if it is time to comunicate with GUI then show something
        if Sim.current_t > self.last_call + self.call_at or force_update:
            if self.temperature_plot is not None:
                # Sending only the data that is already calculated
                self.temperature_plot.plot(x_values=Sim.t[:Sim.current_step_idx],
                                           y_values=Sim.T_x0[:Sim.current_step_idx],
                                           x_experiment_values=Sim.Exp_data.t_data,
                                           y_experiment_values=Sim.Exp_data.T_data)

            # Plotting the heat flux graph
            # When specified, marking it as done and not replotting it again
            if not self.heat_flux_already_plotted and self.heat_flux_plot is not None:
                x_values = None if self.not_replot_heatflux else Sim.t[:Sim.current_step_idx]
                y_values = None if self.not_replot_heatflux else Sim.HeatFlux[:Sim.current_step_idx]
                self.heat_flux_plot.plot(x_values=x_values,
                                         y_values=y_values,
                                         x_experiment_values=Sim.Exp_data.t_data,
                                         y_experiment_values=Sim.Exp_data.q_data)
                if self.not_replot_heatflux:
                    self.heat_flux_already_plotted = True

            # If callback is defined, emit positive value to increment time in GUI
            if self.progress_callback is not None:
                self.progress_callback.emit(1)

            self.last_call += self.call_at

        # TODO: decide how often to read the queue (look if it does not affect performance a lot)
        # TODO: make sure there is not more than 1 message in queue (no leftovers)
        if self.queue is not None and not self.queue.empty():
            # Try to get last item from the queue sent from GUI
            msg = self.queue.get_nowait()
            print(msg)

            # This may seem redundant, but we are guarding against some
            #   unkown msg
            if msg == "stop":
                self.simulation_state = "stopped"
            elif msg == "pause":
                self.simulation_state = "paused"
            elif msg == "continue":
                self.simulation_state = "running"

        # Emit that simulation is not running (not to increment time)
        if self.simulation_state != "running" and self.progress_callback is not None:
            self.progress_callback.emit(0)

        # Returning the current simulation state to be handled by higher function
        return self.simulation_state


class SimulationController:
    """
    Holding variables and defining methods for the simulation
    """

    def __init__(self, Sim, parameters, next_step_func, calculate_error_func,
                 algorithm=None, time_data_location=None,
                 quantity_data_location=None, quantity_and_unit=None,
                 progress_callback=None, queue=None,
                 temperature_plot=None, heat_flux_plot=None,
                 not_replot_heatflux=False, save_results=False):
        self.Sim = Sim
        self.MyCallBack = Callback(progress_callback=progress_callback,
                                   call_at=parameters["callback_period"],
                                   temperature_plot=temperature_plot,
                                   heat_flux_plot=heat_flux_plot,
                                   queue=queue,
                                   not_replot_heatflux=not_replot_heatflux)
        self.algorithm = algorithm
        self.time_data_location = time_data_location
        self.quantity_data_location = quantity_data_location
        self.quantity_and_unit = quantity_and_unit
        self.save_results = save_results
        self.next_step_func = getattr(self.Sim, next_step_func)
        self.calculate_error_func = calculate_error_func
        self.error_norm = None

    def complete_simulation(self):
        """
        Running all the simulation steps, if not stopped
        """

        while self.Sim.current_step_idx < self.Sim.max_step_idx:
            # Processing the callback and getting the simulation state at the same time
            # Then acting accordingly to the current state
            simulation_state = self.MyCallBack(self.Sim)
            if simulation_state == "running":
                # Calling the function that is determining next step
                self.next_step_func()
            elif simulation_state == "paused":
                time.sleep(0.1)
            elif simulation_state == "stopped":
                print("stopping")
                break

        # Calling callback at the very end, to update the plot with complete results
        self.MyCallBack(self.Sim, force_update=True)

        # Determining the error margin through defined function
        self.error_norm = self.calculate_error_func(self.Sim)
        print("Error norm: {}".format(self.error_norm))

        if self.save_results:
            self.save_results_to_csv_file()

        return {"error_value": self.error_norm}

    def save_results_to_csv_file(self):
        """
        Outputs the (semi)results of a simulation into a CSV file and names it
            accordingly.
        """

        # TODO: discuss the possible filename structure
        file_name = "{}-{}.csv".format(self.algorithm,
                                       int(time.time()))

        sim_object = getattr(self, "Sim")
        time_data = getattr(sim_object, self.time_data_location)
        quantity_data = getattr(sim_object, self.quantity_data_location)

        with open(file_name, "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            headers = ["Time [s]", self.quantity_and_unit]
            csv_writer.writerow(headers)

            for time_value, quantity_value in zip(time_data, quantity_data):
                csv_writer.writerow([time_value, quantity_value])
