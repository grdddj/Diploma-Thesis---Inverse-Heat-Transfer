"""
This module is preparing simulation for the PyQT5 GUI.
Theoretically it can be used anywhere, because it just takes an arbitrary plot,
    and calls it's plot() method with the calculated data.

It is now written to support connection with PySide2 GUI in the sense of:
    a) the plot which to update
    b) the queue which to communicate over
However, it can still be used as a standalone module, because we are using
    these connections only when they are set up (are not None)
Therefore it can still be used as a performance tracker, or as a simulation
    module to whatever other GUI will connect to it

TODOS:
    - create documentation for the functions and classes
"""

from NumericalForward import *
import csv
import time
import os
import threading

class NewCallback:
    """

    """
    def __init__(self, Call_at=500.0, ExperimentData=None, heat_flux_plot=None,
                 temperature_plot=None,queue=None, progress_callback=None):
        self.Call_at = Call_at  # specify how often to be called (default is every 50 seccond)
        self.last_call = 0  # placeholder fot time in which the callback was last called

        default_ExperimentData = {"time": None, "temperature": None, "heat_flux": None}
        self.ExperimentData = ExperimentData if ExperimentData is not None else default_ExperimentData

        # Takes reference of some plot, which it should update, and some queue,
        #   through which the GUI will send information.
        # Also save the progress communication channel to update time in GUI
        self.temperature_plot = temperature_plot
        self.heat_flux_plot = heat_flux_plot
        self.queue = queue
        self.progress_callback = progress_callback

        # We do not want to waste time by plotting the same heat_flux values
        #   over and over, so we do that only once, and flag it to be done
        self.heat_flux_already_plotted = False

        # Setting the starting simulation state as "running" - this can be changed
        #   only through the queue by input from GUI
        self.simulation_state = "running"

    def Call(self, Sim, force_update=False):
        """

        """
        # Update the time calculation is in progress
        if Sim.current_t > self.last_call + self.Call_at or force_update == True:  # if it is time to comunicate with GUI then show something
            if self.temperature_plot is not None:
                # Sending only the data that is already calculated
                self.temperature_plot.plot(x_values=Sim.t[:Sim.current_step_idx],
                                         y_values=Sim.T_x0[:Sim.current_step_idx],
                                         x_experiment_values=Sim.Exp_data.t_data,
                                         y_experiment_values=Sim.Exp_data.T_data)

            # Plotting the heat flux graph at the very beginning and marking it done
            if not self.heat_flux_already_plotted and self.heat_flux_plot is not None:
                self.heat_flux_plot.plot(x_values=None,
                                         y_values=None,
                                         x_experiment_values=Sim.Exp_data.t_data,
                                         y_experiment_values=Sim.Exp_data.q_data)
                self.heat_flux_already_plotted = True

            # If callback is defined, emit positive value to increment time in GUI
            if self.progress_callback is not None:
                self.progress_callback.emit(1)

            self.last_call += self.Call_at

        # TODO: decide how often to read the queue (look if it does not affect performance a lot)
        # TODO: make sure there is not more than 1 message in queue (no leftovers)
        if self.queue is not None:
            # Try to get last item from the queue sent from GUI
            try:
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
            # TODO: handle this properly
            except:
                pass

        # Emit the information that simulation is not running (not to increment time)
        if self.simulation_state != "running" and self.progress_callback is not None:
            self.progress_callback.emit(0)

        # Returning the current ismulation state to be handled by make_sim_step()
        return self.simulation_state

class Trial():
    """

    """

    def PrepareSimulation(self, progress_callback, temperature_plot,
                          heat_flux_plot, queue, parameters):
        """

        """
        # This  is how the experiment recorded in DATA.csv was aproximately done
        # my_material = Material(parameters["rho"], parameters["cp"], parameters["lmbd"])
        # self.Sim = Simulation(Length=parameters["object_length"],
        #                       material=my_material,
        #                       N=parameters["number_of_elements"],
        #                       HeatFlux=q_experiment,
        #                       AmbientTemperature=T_amb,
        #                       RobinAlpha=13.5,
        #                       x0=parameters["place_of_interest"])

        self.Sim = Simulation()

        self.MyCallBack = NewCallback(progress_callback=progress_callback,
                                      Call_at=parameters["callback_period"],
                                      temperature_plot=temperature_plot,
                                      heat_flux_plot=heat_flux_plot,
                                      queue=queue)
                                      # ExperimentData=ExperimentData)
        # self.dt = parameters["dt"]
        # self.t_start = t_data[0]
        # self.t_stop = t_data[-1]-1
        # self.Sim.t.append(0.0)  # push start time into time placeholder inside Simulation class
        # self.Sim.T.fill(T_data[0])  # fill initial temperature with value of T0
        # self.Sim.T_record.append(self.Sim.T)  # save initial step

        return True

    def make_sim_step(self):
        """

        """
        while self.Sim.current_step_idx < self.Sim.max_step_idx:
            # Processing the callback and getting the simulation state at the same time
            # Then acting accordingly to the current state
            simulation_state = self.MyCallBack.Call(self.Sim)
            if simulation_state == "running":
                self.Sim.evaluate_one_step()
            elif simulation_state == "paused":
                time.sleep(0.1)
            elif simulation_state == "stopped":
                print("stopping")
                break

        # Calling callback at the very end, to update the plot with complete results
        self.MyCallBack.Call(self.Sim, force_update=True)

        self.ErrorNorm = np.sum(abs(self.Sim.T_x0 - self.Sim.T_data))/len(self.Sim.t[1:])
        self.ErrorNorm = round(self.ErrorNorm, 3)
        print("Error norm: {}".format(self.ErrorNorm))

    def save_results_to_csv_file(self, material="iron"):
        """
        Outputs the (semi)results of a simulation into a CSV file and names it
            accordingly.
        """
        # TODO: discuss the possible filename structure
        file_name = "Classic-{}-{}C-{}s.csv".format(material, int(self.Sim.T_x0[0]),
                                            int(self.Sim.t[-1]))

        # If for some reason there was already the same file, rather not
        #   overwrite it, but create a new file a timestamp as an identifier
        if os.path.isfile(file_name):
            file_name = file_name.split(".")[0] + "-" + str(int(time.time())) + ".csv"

        with open(file_name, "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            headers = ["Time [s]", "Temperature [C]"]
            csv_writer.writerow(headers)

            for time_value, temperature in zip(self.Sim.t, self.Sim.T_x0):
                csv_writer.writerow([time_value, temperature])

def run_test(temperature_plot=None, heat_flux_plot=None, progress_callback=None,
             amount_of_trials=1, queue=None, parameters=None, SCENARIO_DESCRIPTION=None):
    """

    """
    app = Trial()

    # The description of tested scenario, what was changed etc.
    if SCENARIO_DESCRIPTION is None:
        SCENARIO_DESCRIPTION = "SpeedTest"

    # If there are no inputted parameters for some reason, replace it with default ones
    if parameters is None:
        parameters = {
            "rho": 7850,
            "cp": 520,
            "lmbd": 50,
            "dt": 1,
            "object_length": 0.01,
            "place_of_interest": 0.0045,
            "number_of_elements": 100,
            "callback_period": 500
        }

    now = time.time()

    # Running the simulation for specific amount of trials
    for i in range(amount_of_trials):
        print("Current thread: {}".format(threading.currentThread().getName()))

        x = time.time()
        app.PrepareSimulation(progress_callback=progress_callback,
                              temperature_plot=temperature_plot,
                              heat_flux_plot=heat_flux_plot,
                              queue=queue,
                              parameters=parameters)
        y = time.time()
        print("PrepareSimulation: {}".format(round(y - x, 3)))
        app.make_sim_step()
        z = time.time()
        print("make_sim_step: {}".format(round(z - y, 3)))
        # progress_callback.emit("ggf")
        app.save_results_to_csv_file()

    print(80*"*")

    average_loop_time = (time.time() - now) / amount_of_trials
    average_loop_time = round(average_loop_time, 3)
    print("average_loop_time: {} seconds".format(average_loop_time))

    # Saving the results to have access to them later
    # (useful when comparing and trying to remember what was tried and what not)

    # Creating a directory "Performace" if it does not exist already
    WORKING_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
    directory_for_results = os.path.join(WORKING_DIRECTORY, 'Performance')
    if not os.path.isdir(directory_for_results):
        os.mkdir(directory_for_results)

    # Getting the file appropriate name
    file_name = "{}/{}s-{}e-{}.txt".format(directory_for_results, average_loop_time, app.ErrorNorm, SCENARIO_DESCRIPTION)

    # Saving useful info to the file
    with open(file_name, "w") as file:
        file.write("DESCRIPTION: {}\n".format(SCENARIO_DESCRIPTION))
        file.write("average_loop_time: {}\n".format(average_loop_time))
        file.write("amount_of_trials: {}\n".format(amount_of_trials))
        file.write("number_of_elements: {}\n".format(parameters["number_of_elements"]))
        file.write("dt: {}\n".format(parameters["dt"]))
        file.write("ErrorNorm: {}\n".format(app.ErrorNorm))

    # Returning the dictionary with arbitrary information for the GUI to be notified
    return {"error_value": app.ErrorNorm}

if __name__ == '__main__':
    run_test(amount_of_trials=2, SCENARIO_DESCRIPTION="SpeedTest")
