"""
This (dirty) module is supposed to offer performance testing of the algorithms
    we use.
It's supposed use is to try improvements in NumericalForward, which is being
    imported here, run this script, and observe the output in the terminal
    and in the generated .txt file.
This way we can track the improvements through the time, and quickly
    experiment with new things.
After completion, NumericalInverse could be tested with a similar way.

RESULTS WORTH NOTING:
- After implementing the default A and b, the time dropped from 5,5 to 3,5 seconds
    (in a scenario without ever changing dt or theta, so no recalculating)
"""

from NumericalForward import *
import matplotlib.pyplot as plt
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
        self.Sim = Simulation()
        self.MyCallBack = NewCallback()
        return True

    def make_sim_step(self):
        """
        """
        self.loop_amount = 0
        while self.Sim.current_step_idx < self.Sim.max_step_idx:
            self.Sim.evaluate_one_step()  # evaluate Temperaures at step k
            self.MyCallBack.Call(self.Sim)
            self.loop_amount += 1

        self.ErrorNorm = np.sum(abs(self.Sim.T_x0 - self.Sim.T_data))/len(self.Sim.t[1:])
        self.ErrorNorm = round(self.ErrorNorm, 3)
        print("Error norm: {}".format(self.ErrorNorm))

    def plot_all(self):
        plt.plot(self.Sim.t, self.Sim.T_x0)
        plt.plot(self.Sim.t, self.Sim.T_data)
        plt.show()


if __name__ == '__main__':
    app = Trial()

    # The description of tested scenario, what was changed etc.
    SCENARIO_DESCRIPTION = "PERF"

    amount_of_trials = 3

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
        file.write("number_of_elements: {}\n".format(app.Sim.N))
        file.write("loop_amount: {}\n".format(app.loop_amount))
        file.write("dt: {}\n".format(app.Sim.dt))
        file.write("ErrorNorm: {}\n".format(app.ErrorNorm))

    # app.plot_all()
