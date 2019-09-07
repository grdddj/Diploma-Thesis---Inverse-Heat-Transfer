#!/usr/bin/env python3

from NumericalForward import *
import csv

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
T_experiment = MakeDataCallable(t_data, T_data)  # colapse data into callable function T_experiment(t)
T_amb = MakeDataCallable(t_data, T_amb_data)  # colapse data into callable function T_amb(t)
# Look into NumericalForward.py for details

# This  is how the experiment recorded in DATA.csv was aproximately done
SteinlessSteel = Material(7850, 490, 13.5)
TestSim = Simulation(Length=0.010, Material=SteinlessSteel, N=100, HeatFlux=test_q, AmbientTemperature=T_amb, RobinAlpha=13.5)
MyCallBack = DefaultCallBack(x0=0.00445, plot_limits=[t_data[0], t_data[-1], min(T_data), max(T_data)], ExperimentData=(t_data, T_data))

ForwardSimulation(TestSim, dt=1.0, T0=T_data[0], t_stop=max(t_data)-1, CallBack=MyCallBack)

# we check if Simulationn fits the experimental data
ErrorNorm = np.sum(abs(MyCallBack.TempHistoryAtPoint_x0 - T_experiment(TestSim.t[1:])))/len(TestSim.t[1:])  # average temperature error

print(ErrorNorm)  # the reason why it is not completely the same is because the actual experiment was not complentely one-dimensional (that is often the case)
if ErrorNorm < 0.5:
    print("Test passed")
else:
    print("Test failed")

# I will send you The inverse solver later
# I have to think how to make it compatible with NumericalForward.py in particular with the function EvaluateNewStep
