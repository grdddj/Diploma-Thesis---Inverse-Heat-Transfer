"""
TODOS:
    - authomatic saving of the results in CSV file and info png
        - name it according to the material f.e.
    - capturing of the result (error) and outputting it
        - show that the simulation has ended
    - measuring the time the simulation has been in progress
    - offer the creation of custom material/custom properties
        - consider showing the properties in the menu/next to it
        - consider moving materials to the DB (SQLite3)
    - include some labels and legends in the graph
    - improve the design of the menus and buttons
    - include second graph showing heat flux
"""
#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
from tkinter import font
import os

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from NumericalForward import *
import csv
import time

class NewCallback:
    """

    """
    def __init__(self, Call_at=100.0, plot_limits=[0, 5000, 20, 40], x0=0, ExperimentData=None):
        self.Call_at = Call_at  # specify how often to be called (default is every 50 seccond)
        self.last_call = 0  # placeholder fot time in which the callback was last called
        self.plot_limits = plot_limits  # axis limits to make plot looking "better"
        self.x0 = x0  # x positinon of the temperature we are interested in
        self.TempHistoryAtPoint_x0 = []  # We can be saving data of temperature from specific point in space (x0)
        self.ExperimentData = ExperimentData

    def Call(self, Sim):
        # https://docs.scipy.org/doc/numpy/reference/generated/numpy.interp.html
        self.TempHistoryAtPoint_x0.append(np.interp(self.x0, Sim.x, Sim.T))  # interpolate temperature value at position x0 from point around and save it
        if Sim.t[-1] > self.last_call + self.Call_at:  # if it is time to comunicate with GUI then show something

            # Refreshing the graph with all the new time and temperature values
            app.frames[GraphView].refresh_graph(Sim.t[1:], self.TempHistoryAtPoint_x0, self.ExperimentData[0], self.ExperimentData[1])

            time.sleep(0.05) # without sleeping it is getting unresponsive sometimes

            print(f"Temperature at x0: {self.TempHistoryAtPoint_x0[-1]} at time {Sim.t[-1]} flux: {Sim.HeatFlux(Sim.t[-1])}")
            self.last_call += self.Call_at


class HeatTransfer(tk.Tk):
    """

    """
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        # tk.Tk.iconbitmap(self, default="myIcon.ico")
        tk.Tk.wm_title(self, "Heat Transfer")

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        for each_frame in [GraphView]:
            frame = each_frame(container, self)

            self.frames[each_frame] = frame

            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(GraphView)

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()


class GraphView(tk.Frame):
    """

    """
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        # Top frame for the settings etc.
        self.frame_top = tk.Frame(self, bg="#42b6f4", bd=5)
        self.frame_top.place(relx=0.5, rely=0.1, relwidth=0.7, relheight=0.2, anchor="n")

        self.initialize_menu(self.frame_top)

        self.button = tk.Button(self.frame_top, text="Run", bg="grey", fg="black", font=("Calibri", 15), command=lambda: self.run_the_test_with_chosen_material())
        self.button.place(relx=0.75, rely=0, relheight=1, relwidth=0.25)

        # Bottom frame for the graph(s)
        self.frame_bottom = tk.Frame(self, bg="#42b6f4", bd=10)
        self.frame_bottom.place(relx=0.5, rely=0.35, relwidth=0.7, relheight=0.6, anchor="n")

        self.initialize_graph(self.frame_bottom)

    def initialize_menu(self, container):
        """

        """
        self.MATERIALS_LIST = self.get_materials_from_csv_file()

        print(len(self.MATERIALS_LIST))
        self.material_names = [material["name"] for material in self.MATERIALS_LIST]

        # Defining the OptionMenu for the choice of material
        self.material_choice = tk.StringVar(container)
        self.material_choice.set(self.material_names[0]) # default value

        self.menu = ttk.OptionMenu(container, self.material_choice, *self.material_names)
        self.menu.place(relx=0, rely=0, relheight=0.25, relwidth=0.25)

    def initialize_graph(self, container):
        """

        """
        f = Figure(figsize=(5,5), dpi=100)
        self.a = f.add_subplot(111)

        self.a.plot([], [])

        self.canvas = FigureCanvasTkAgg(f, container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        # self.canvas.get_tk_widget().place(relx=0.05, rely=0.3, relwidth=0.9, relheight=0.65)

    def refresh_graph(self, x_values, y_values, x_experiment_values=None, y_experiment_values=None):
        """

        """
        print("refreshed!!!")
        self.a.cla()
        self.a.plot(x_values, y_values)
        if x_experiment_values is not None and y_experiment_values is not None:
            self.a.plot(x_experiment_values, y_experiment_values)
        self.canvas.draw()

    def get_materials_from_csv_file(self):
        """

        """

        materials_list = []
        with open("metals_properties.csv", "r") as materials_file:
            csvReader = csv.reader(materials_file)
            next(csvReader, None)  # skip first line (headers)
            for row in csvReader:
                if row:
                    material_dictionary = {}
                    material_dictionary["name"] = row[0]
                    material_dictionary["rho"] = row[2]
                    material_dictionary["cp"] = row[3]
                    material_dictionary["lmbd"] = row[4]
                    materials_list.append(material_dictionary)

        return materials_list

    def run_the_test_with_chosen_material(self):
        """

        """
        chosen_material = self.material_choice.get()

        for material in self.MATERIALS_LIST:
            if material["name"] == chosen_material:
                rho = int(material["rho"])
                cp = int(material["cp"])
                lmbd = int(material["lmbd"])
                break

        self.run_the_test(rho, cp, lmbd)

    def run_the_test(self, rho, cp, lmbd):
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
        T_experiment = MakeDataCallable(t_data, T_data)  # colapse data into callable function T_experiment(t)
        T_amb = MakeDataCallable(t_data, T_amb_data)  # colapse data into callable function T_amb(t)
        # Look into NumericalForward.py for details

        # This  is how the experiment recorded in DATA.csv was aproximately done
        SteinlessSteel = Material(rho, cp, lmbd)
        TestSim = Simulation(Length=0.010, Material=SteinlessSteel, N=100, HeatFlux=test_q, AmbientTemperature=T_amb, RobinAlpha=13.5)
        MyCallBack = NewCallback(x0=0.00445, plot_limits=[t_data[0], t_data[-1], min(T_data), max(T_data)], ExperimentData=(t_data, T_data))

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



if __name__ == '__main__':
    app = HeatTransfer()
    app.state("zoomed")

    app.mainloop()
