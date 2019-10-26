"""
This module is serving for running the Inverse simulation.
It can be run separately or from the GUI, in which case it will be updating the plot.
"""


from NumericalInverse import *
import csv
import time
import os

class InverseCallback:
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

        # Setting the starting simulation state as "running" - this can be changed
        #   only through the queue by input from GUI
        self.simulation_state = "running"

    def Call(self, Sim, force_update=False):
        """

        """
        # Update the time calculation is in progress
        if Sim.t[-1] > self.last_call + self.Call_at or force_update == True:  # if it is time to comunicate with GUI then show something
            if self.temperature_plot is not None:
                self.temperature_plot.plot(x_values=Sim.t[1:],
                                         y_values=Sim.T_x0,
                                         x_experiment_values=self.ExperimentData["time"],
                                         y_experiment_values=self.ExperimentData["temperature"])

            if self.heat_flux_plot is not None:
                # Showing only the already calculated part of the heat flux
                calculated_length = len(Sim.T_x0)
                self.heat_flux_plot.plot(x_values=Sim.HeatFlux.x[:calculated_length],
                                         y_values=Sim.HeatFlux.y[:calculated_length],
                                         x_experiment_values=self.ExperimentData["time"],
                                         y_experiment_values=self.ExperimentData["heat_flux"])

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

class InverseTrial:
    """

    """

    def PrepareSimulation(self, progress_callback, temperature_plot,
                          heat_flux_plot, queue, parameters):
        """

        """
        self.t_data = []  # experimental data of time points
        self.T_data = []  # experimental data of temperature data at x0=0.008
        self.q_data = []  # experimental data of Measured HeatFluxes at left boundary
        T_amb_data = []  # experimental data of ambinet temperature

        # read from datafile (might look like this)
        with open('DATA.csv') as csvDataFile:
            csvReader = csv.reader(csvDataFile)
            next(csvReader, None)  # skip first line (headers)
            for row in csvReader:
                self.t_data.append(float(row[0]))
                self.T_data.append(float(row[1]))
                self.q_data.append(float(row[2]))
                T_amb_data.append(float(row[3]))

        self.q_experiment = MakeDataCallable(self.t_data, self.q_data)  # colapse data into callable function test_q(t)
        T_experiment = MakeDataCallable(self.t_data, self.T_data)  # colapse data into callable function T_experiment(t)
        T_amb = MakeDataCallable(self.t_data, T_amb_data)  # colapse data into callable function T_amb(t)
        # Look into NumericalForward.py for details

        ExperimentData = {
            "time": self.t_data,
            "temperature": self.T_data,
            "heat_flux": self.q_data
        }

        self.window_span = parameters["window_span"]

        my_material = Material(parameters["rho"], parameters["cp"], parameters["lmbd"])
        self.Sim = Simulation(Length=parameters["object_length"],
                              Material=my_material,
                              N=parameters["number_of_elements"],
                              HeatFlux=self.q_experiment,
                              AmbientTemperature=T_amb,
                              RobinAlpha=10.5,
                              x0=parameters["place_of_interest"])

        self.Problem = InverseProblem(self.Sim,
                                      dt=parameters["dt"],
                                      data_T=T_experiment)

        self.MyCallBack = InverseCallback(progress_callback=progress_callback,
                                          Call_at=parameters["callback_period"],
                                          temperature_plot=temperature_plot,
                                          heat_flux_plot=heat_flux_plot,
                                          queue=queue,
                                          ExperimentData=ExperimentData)

    def make_inverse_step(self):
        """

        """
        while self.Problem.Sim.t[-1] < self.t_data[-1]-100:
            # Processing the callback and getting the simulation state at the same time
            # Then acting accordingly to the current state
            simulation_state = self.MyCallBack.Call(self.Sim)
            if simulation_state == "running":
                SolveInverseStep(self.Problem, window_span=self.window_span, tolerance=1e-6)
            elif simulation_state == "paused":
                import random
                if random.random() < 0.1:
                    print("sleep")
                time.sleep(0.1)
            elif simulation_state == "stopped":
                print("stopping")
                break

        # Calling callback at the very end, to update the plot with complete results
        self.MyCallBack.Call(self.Problem.Sim, force_update=True)

        # TODO: review this, as it might not be correct
        heat_flux_length = len(self.Sim.t)
        self.ErrorNorm = np.sum(abs(self.Problem.Sim.HeatFlux.y[:heat_flux_length] - self.q_experiment(self.Sim.t)))/heat_flux_length
        self.ErrorNorm = round(self.ErrorNorm, 3)
        print("Error norm: {}".format(self.ErrorNorm))

    def save_results_to_csv_file(self, material="iron"):
        """
        Outputs the (semi)results of a simulation into a CSV file and names it
            accordingly.
        """
        # TODO: discuss the possible filename structure
        file_name = "Inverse-{}-{}C-{}s.csv".format(material, int(self.Sim.T_x0[0]),
                                                    int(self.Sim.HeatFlux.x[-1]))

        # If for some reason there was already the same file, rather not
        #   overwrite it, but create a new file a timestamp as an identifier
        if os.path.isfile(file_name):
            file_name = file_name.split(".")[0] + "-" + str(int(time.time())) + ".csv"

        with open(file_name, "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            headers = ["Time [s]", "Temperature [C]"]
            csv_writer.writerow(headers)

            for time_value, temperature in zip(self.Sim.HeatFlux.x, self.Sim.HeatFlux.y):
                csv_writer.writerow([time_value, temperature])


def run_test(temperature_plot=None, heat_flux_plot=None, progress_callback=None,
             amount_of_trials=1, queue=None, parameters=None, SCENARIO_DESCRIPTION=None,
             save_results=False):
    """

    """
    app = InverseTrial()

    # The description of tested scenario, what was changed etc.
    if SCENARIO_DESCRIPTION is None:
        SCENARIO_DESCRIPTION = "INVERSE"

    # If there are no inputted parameters for some reason, replace it with default ones
    if parameters is None:
        parameters = {
            "rho": 7850,
            "cp": 520,
            "lmbd": 50,
            "dt": 50,
            "object_length": 0.01,
            "place_of_interest": 0.0045,
            "number_of_elements": 100,
            "callback_period": 500,
            "window_span": 2
        }

    app.PrepareSimulation(progress_callback=progress_callback,
                          temperature_plot=temperature_plot,
                          heat_flux_plot=heat_flux_plot,
                          queue=queue,
                          parameters=parameters)

    x = time.time()
    # loop (higher window_span makes it slower, there is always an ideal value regarding speed vs accuracy)
    app.make_inverse_step()
    if save_results:
        app.save_results_to_csv_file()

    return {"error_value": app.ErrorNorm}

    # fig1 = plt.figure()
    # plt.plot(app.t_data, app.q_data)
    # plt.plot(app.Problem.Sim.HeatFlux.x, app.Problem.Sim.HeatFlux.y)
    #
    # fig2 = plt.figure()
    # plt.plot(app.t_data, app.T_data)
    # plt.plot(app.Problem.Sim.t, app.Problem.Sim.T_x0)
    #
    # plt.show()

if __name__ == '__main__':
    run_test()
