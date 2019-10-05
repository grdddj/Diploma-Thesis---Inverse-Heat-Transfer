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
"""

from NumericalForward import *
import csv
import time
import os
import threading

class NewCallback:
    """
    """
    def __init__(self, Call_at=200.0, x0=0, ExperimentData=None, plot_to_update=None, queue=None):
        self.Call_at = Call_at  # specify how often to be called (default is every 50 seccond)
        self.last_call = 0  # placeholder fot time in which the callback was last called
        self.ExperimentData = ExperimentData

        # Takes reference of some plot, which it should update, and some queue,
        #   through which the GUI will send information
        self.plot_to_update = plot_to_update
        self.queue = queue

        # Setting the starting simulation state as "running" - this can be changed
        #   only through the queue by input from GUI
        self.simulation_state = "running"

    def Call(self, Sim):
        """
        """
        # Update the time calculation is in progress
        if Sim.t[-1] > self.last_call + self.Call_at:  # if it is time to comunicate with GUI then show something
            if self.plot_to_update is not None:
                self.plot_to_update.plot(Sim.t[1:],Sim.T_x0)

            self.last_call += self.Call_at

        # TODO: decide how often to read the queue (look if it does not affect performance a lot)
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

        # Returning the current ismulation state to be handled by make_sim_step()
        return self.simulation_state

class Trial():
    """
    """

    def PrepareSimulation(self, plot, queue):
        """
        """
        t_data = []  # experimental data of time points
        T_data = []  # experimental data of temperature data at x0=0.008
        q_data = []  # experimental data of Measured HeatFluxes at left boundary
        T_amb_data = []  # experimental data of ambinet temperature

        # read from datafile (might look like this)
        with open('DATA.csv') as csvDataFile:
            csvReader = csv.reader(csvDataFile)
            next(csvReader, None)  # skip first line (headers)
            for row in csvReader:
                t_data.append(float(row[0]))
                T_data.append(float(row[1]))
                q_data.append(float(row[2]))
                T_amb_data.append(float(row[3]))

        test_q = MakeDataCallable(t_data, q_data)  # colapse data into callable function test_q(t)
        self.T_experiment = MakeDataCallable(t_data, T_data)  # colapse data into callable function T_experiment(t)
        T_amb = MakeDataCallable(t_data, T_amb_data)  # colapse data into callable function T_amb(t)
        # Look into NumericalForward.py for details

        # This  is how the experiment recorded in DATA.csv was aproximately done
        my_material = Material(self.rho, self.cp, self.lmbd)
        self.Sim = Simulation(Length=self.object_length,
                              Material=my_material,
                              N=self.number_of_elements,
                              HeatFlux=test_q,
                              AmbientTemperature=T_amb,
                              RobinAlpha=13.5,
                              x0=self.place_of_interest)

        self.MyCallBack = NewCallback(plot_to_update=plot, queue=queue)
        self.t_start = t_data[0]
        self.t_stop = t_data[-1]-1
        self.Sim.t.append(0.0)  # push start time into time placeholder inside Simulation class
        self.Sim.T.fill(T_data[0])  # fill initial temperature with value of T0
        self.Sim.T_record.append(self.Sim.T)  # save initial step

        return True

    def make_sim_step(self):
        """
        """
        self.loop_amount = 0
        while self.Sim.t[-1] < self.t_stop:
            # Processing the callback and getting the simulation state at the same time
            # Then acting accordingly to the current state
            simulation_state = self.MyCallBack.Call(self.Sim)
            if simulation_state == "running":
                dt = min(self.dt, self.t_stop-self.Sim.t[-1])  # checking if not surpassing t_stop
                EvaluateNewStep(self.Sim, dt, 0.5)  # evaluate Temperaures at step k
                self.loop_amount += 1
            elif simulation_state == "paused":
                time.sleep(0.1)
            elif simulation_state == "stopped":
                print("stopping")
                break

        self.ErrorNorm = np.sum(abs(self.Sim.T_x0 - self.T_experiment(self.Sim.t[1:])))/len(self.Sim.t[1:])
        self.ErrorNorm = round(self.ErrorNorm, 3)
        print("Error norm: {}".format(self.ErrorNorm))

def run_test(plot=None, progress_callback=None, amount_of_trials=1, queue=None):
    app = Trial()

    # The description of tested scenario, what was changed etc.
    SCENARIO_DESCRIPTION = "PySide2"

    app.rho = 7850
    app.cp = 520
    app.lmbd = 50

    app.dt = 1
    app.object_length = 0.01
    app.place_of_interest = 0.0045
    app.number_of_elements = 100

    now = time.time()

    # Running the simulation for specific amount of trials
    for i in range(amount_of_trials):
        print("Current thread: {}".format(threading.currentThread().getName()))

        x = time.time()
        app.PrepareSimulation(plot, queue)
        y = time.time()
        print("PrepareSimulation: {}".format(round(y - x, 3)))
        app.make_sim_step()
        z = time.time()
        print("make_sim_step: {}".format(round(z - y, 3)))
        # progress_callback.emit("ggf")

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
        file.write("number_of_elements: {}\n".format(app.number_of_elements))
        file.write("loop_amount: {}\n".format(app.loop_amount))
        file.write("dt: {}\n".format(app.dt))
        file.write("ErrorNorm: {}\n".format(app.ErrorNorm))


    return "I am finally freee!"


if __name__ == '__main__':
    run_test(amount_of_trials=5)
