"""
This (dirty) module is supposed to offer performance testing of the algorithms
    we use.
It's supposed use is to try improvements in NumericalForward, which is being
    imported here, run this script, and observe the output in the terminal
    and in the generated .txt file.
This way we can track the improvements through the time, and quickly
    experiment with new things.
After completion, NumericalInverse could be tested with a similar way.
"""

from NumericalForward import *
import csv
import time
import os

class NewCallback:
    """
    """
    def __init__(self, Call_at=200.0, x0=0, ExperimentData=None):
        self.Call_at = Call_at  # specify how often to be called (default is every 50 seccond)
        self.last_call = 0  # placeholder fot time in which the callback was last called
        self.ExperimentData = ExperimentData

    def Call(self, Sim):
        """
        """
        # Update the time calculation is in progress
        if Sim.t[-1] > self.last_call + self.Call_at:  # if it is time to comunicate with GUI then show something
            # print(Sim.t[-1])
            # Refreshing the graph with all the new time and temperature values
            self.last_call += self.Call_at

        return True

class Trial():
    """
    """

    def PrepareSimulation(self):
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

        self.MyCallBack = NewCallback()
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
            dt = min(self.dt, self.t_stop-self.Sim.t[-1])  # checking if not surpassing t_stop
            EvaluateNewStep(self.Sim, dt, 0.5)  # evaluate Temperaures at step k
            self.MyCallBack.Call(self.Sim)
            self.loop_amount += 1

        self.ErrorNorm = np.sum(abs(self.Sim.T_x0 - self.T_experiment(self.Sim.t[1:])))/len(self.Sim.t[1:])
        self.ErrorNorm = round(self.ErrorNorm, 3)
        print("Error norm: {}".format(self.ErrorNorm))


if __name__ == '__main__':
    app = Trial()

    # The description of tested scenario, what was changed etc.
    SCENARIO_DESCRIPTION = "Trial"

    app.rho = 7850
    app.cp = 520
    app.lmbd = 50

    app.dt = 10
    app.object_length = 0.01
    app.place_of_interest = 0.0045
    app.number_of_elements = 100

    amount_of_trials = 10

    now = time.time()

    # Running the simulation for specific amount of trials
    for _ in range(amount_of_trials):
        x = time.time()
        app.PrepareSimulation()
        y = time.time()
        print("PrepareSimulation: {}".format(round(y - x, 3)))
        app.make_sim_step()
        z = time.time()
        print("make_sim_step: {}".format(round(z - y, 3)))

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
