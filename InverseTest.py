from NumericalInverse import *
import csv
import time

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

q_experiment = MakeDataCallable(t_data, q_data)  # colapse data into callable function test_q(t)
T_experiment = MakeDataCallable(t_data, T_data)  # colapse data into callable function T_experiment(t)
T_amb = MakeDataCallable(t_data, T_amb_data)  # colapse data into callable function T_amb(t)
# Look into NumericalForward.py for details

parameters = {
    "rho": 7850,
    "cp": 490,
    "lmbd": 13.5,
    "dt": 1,
    "object_length": 0.01,
    "place_of_interest": 0.00445,
    "number_of_elements": 100
}
my_material = Material(parameters["rho"], parameters["cp"], parameters["lmbd"])
Sim = Simulation(Length=parameters["object_length"],
                      Material=my_material,
                      N=parameters["number_of_elements"],
                      HeatFlux=q_experiment,
                      AmbientTemperature=T_amb,
                      RobinAlpha=10.5,
                      x0=parameters["place_of_interest"])


Problem = InverseProblem(Sim, dt=5.0, data_T=T_experiment)
x = time.time()
# loop (higher window_span makes it slower, there is always an ideal value regarding speed vs accuracy)
while Problem.Sim.t[-1] < t_data[-1]-100:
    SolveInverseStep(Problem, window_span=3, tolerance=1e-6)
    print("Elapsed Time: %.2f seconds." % (time.time()-x))

fig1 = plt.figure()
plt.plot(t_data, q_data)
plt.plot(Problem.Sim.HeatFlux.x, Problem.Sim.HeatFlux.y)

fig2 = plt.figure()
plt.plot(t_data, T_data)
plt.plot(Problem.Sim.t, Problem.Sim.T_x0)

plt.show()
