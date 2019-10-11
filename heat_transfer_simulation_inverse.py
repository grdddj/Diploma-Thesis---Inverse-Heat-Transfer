"""
This module is serving for running the Inverse simulation.
It can be run separately or from the GUI, in which case it will be updating the plot.
"""


from NumericalInverse import *
import csv
import time

class InverseCallback:
    """

    """
    def __init__(self, Call_at=500.0, ExperimentData=None, plot_to_update=None, queue=None, progress_callback=None):
        self.Call_at = Call_at  # specify how often to be called (default is every 50 seccond)
        self.last_call = 0  # placeholder fot time in which the callback was last called
        self.ExperimentData = ExperimentData if ExperimentData is not None else (None, None)

        # Takes reference of some plot, which it should update, and some queue,
        #   through which the GUI will send information.
        # Also save the progress communication channel to update time in GUI
        self.plot_to_update = plot_to_update
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
            print("TIME!!")
            if self.plot_to_update is not None:
                print("PLOT")
                print("sim.t-1 length: {}".format(len(Sim.t[1:])))
                print("HeatFlux.y length: {}".format(len(Sim.HeatFlux.y)))
                print("HeatFlux.x length: {}".format(len(Sim.HeatFlux.x)))
                # self.plot_to_update.plot(x_values=Sim.t[1:],
                self.plot_to_update.plot(x_values=Sim.HeatFlux.x,
                                         y_values=Sim.HeatFlux.y)
                                         # x_experiment_values=self.ExperimentData[0],
                                         # y_experiment_values=self.ExperimentData[1])

            # If callback is defined, emit positive value to increment time in GUI
            if self.progress_callback is not None:
                self.progress_callback.emit(1)

            self.last_call += self.Call_at

        # TODO: decide how often to read the queue (look if it does not affect performance a lot)
        # TODO: make sure there is not more than 1 message in queue (no leftovers)
        if self.queue is not None:
            "QUEUE"
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

    def PrepareSimulation(self, progress_callback, plot, queue, parameters):
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

        q_experiment = MakeDataCallable(self.t_data, self.q_data)  # colapse data into callable function test_q(t)
        T_experiment = MakeDataCallable(self.t_data, self.T_data)  # colapse data into callable function T_experiment(t)
        T_amb = MakeDataCallable(self.t_data, T_amb_data)  # colapse data into callable function T_amb(t)
        # Look into NumericalForward.py for details

        my_material = Material(parameters["rho"], parameters["cp"], parameters["lmbd"])
        self.Sim = Simulation(Length=parameters["object_length"],
                              Material=my_material,
                              N=parameters["number_of_elements"],
                              HeatFlux=q_experiment,
                              AmbientTemperature=T_amb,
                              RobinAlpha=10.5,
                              x0=parameters["place_of_interest"])

        self.Problem = InverseProblem(self.Sim,
                                      dt=parameters["dt"],
                                      data_T=T_experiment)

        self.MyCallback = InverseCallback(progress_callback=progress_callback,
                                          Call_at=parameters["callback_period"],
                                          plot_to_update=plot,
                                          queue=queue,
                                          ExperimentData=(self.t_data, self.T_data))

    def make_inverse_step(self):
        """

        """
        while self.Problem.Sim.t[-1] < self.t_data[-1]-100:
            SolveInverseStep(self.Problem, window_span=2, tolerance=1e-6)
            # print("Elapsed Time: %.2f seconds." % (time.time()-x))
            self.MyCallback.Call(self.Problem.Sim)

        # TODO: WHY ARE THE CALLBACKS NOT WOTKING FURTHER WAY????
        #     AttributeError: 'InverseTrial' object has no attribute 'MyCallBack'
        # self.MyCallBack.Call(self.Problem.Sim, force_update=True)

        # while self.Problem.Sim.t[-1] < self.t_data[-1]-100:
        #     # Processing the callback and getting the simulation state at the same time
        #     # Then acting accordingly to the current state
        #     print("preparing to clal callback")
        #     simulation_state = self.MyCallBack.Call(self.Sim)
        #     if simulation_state == "running":
        #         SolveInverseStep(self.Problem, window_span=2, tolerance=1e-6)
        #     elif simulation_state == "paused":
        #         import random
        #         if random.random() < 0.1:
        #             print("sleep")
        #         time.sleep(0.1)
        #     elif simulation_state == "stopped":
        #         print("stopping")
        #         break
        #
        # self.MyCallBack.Call(self.Problem.Sim, force_update=True)

def run_test(plot=None, progress_callback=None, amount_of_trials=1,
             queue=None, parameters=None, SCENARIO_DESCRIPTION=None):
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
            "callback_period": 500
        }

    app.PrepareSimulation(progress_callback, plot, queue, parameters)

    x = time.time()
    # loop (higher window_span makes it slower, there is always an ideal value regarding speed vs accuracy)
    app.make_inverse_step()

    return {"error_value": 3.14}

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
