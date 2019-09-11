"""
TODOS:
    - authomatic saving of the results in CSV file and into png
        - name it according to the material f.e.
    - offer the creation of custom material/custom properties
        - consider showing the properties in the menu/next to it
        - consider moving materials to the DB (SQLite3)
    - improve the design of the menus and buttons
    - include second graph showing heat flux
    - look up the cx_Freeze to-exe module, as pyinstaller produces 300 MB .exe
        - cx_Freeze offers deletion of unused libraries (scipy etc.)
    - create second thread that is responsible for the calculation
        - IDEA: running the calculation as a separate script, output the
                results to the text_file and draw it continually from there
    - offer "run calculation on background" possibility (without any visual output)
"""
""" TEMPORARY COMMENT:
    I had fixed the responsivenes bug when running the app in serial but...
    I do agree with the approach to make the calculation loop completely separate process
    The communication should be done through some custom message parsing interface.
    For example (as you say correctly in my opinion), the calculation loop can continuously
    output the results to some temporary file(s) while continuously checking values in another text file
    to obtain information on what it should do next (stop, continue, pause or something).

    Something in the sense of:
    def run_stop_button_action(self):

        if self.button_run_stop["text"] == "Run":
            self.Input_File.set_Stop_Value(False)
            # Runs completely separate thing
            os.system("start python3 CalculationScript.py self.pathToInputFile self.pathToOutputFile")
            # or even with fenics
            # os.system("start mpirun -n 10 python3 ParallelCalculationScript.py self.pathToInputFile self.pathToOutputFile")
        else:
            self.Input_File.set_Stop_Value(True)
        return True

    - I has several advantages:
        1) If the GUI crashes the calculation loop does not, which is nice
        2) If the calculation loop crashes the GUI does not, which is also nice
        3) If the calculation loop crashes we will still have the intermediate
           results in the output file so we can continue from there after reboot, which is really nice
           regarding the fact that some more complex calculation can take quite a while to finish.
        4) The calculation loop will not be slowed down by updating the plots,
           since the GUI will take care of that as often as it will comfortably handle.
        5) If we implement some parallelism inside the calculation loop itself,
           which seems super easy with FeniCS (at least what I have tried with it - not completely
           sure about the inverse stuff) and it will run let's say with 10 threads, it will be
           much easier to handle the responsiveness of the GUI since it can still be run in serial.

    But there might be some caveat I did not think of and it can backfire heavily....
    And therefore I would totally leave that for later!!!

------------------
    I really appreciate the improvement you had done, which makes it more
        than good enough for most purposes now - and after my today's unsuccessfull tries
        to implement multiprocessing/threading I certainly agree further optimization
        should be left for the future.

    The idea of putting more threads or processes into the computation itself
        sounds very appealing, and should certainly be tried later.

    What I spent some time today was trying to implement some basic multiprocessing
        and multithreading with the shared variable (Queue) between the calculating
        piece of program and the GUI - with GUI checking the variable for new
        values in regular intervals.
    I started with multiprocessing, and I was constantly receiving some "pickling"
        error from TKinter, which after googling it is basically saying
        the TKinter cannot be used at all with multiprocessing.
    With multithreading I had more luck, managed to make it run, but it was
        slow as hell - the whole simulation took about 35 seconds (compared to
        approximately 10 in a normal case).
    I find this strange, because the other computing thread should not do the
        calculations anyhow slower than the main thread - so I suspect the real
        time-sink is caused by the overhead and probably communication between
        the threads over the shared variable.

    In the end I did not make any changes to the master, just put back the error-showing and
        fixed the legend-plotting. I also slightly modified the max_iter and refreshing
        period, as it made the whole process faster with no visible effect on responsiveness.

    As I wrote all above, I start thinking more and more that the solution with
        having a separate script for the calculation - boosted on many threads -
        and communicating with a GUI through a file (I really liked your definition
        of "message parsing interface") can be the way to go.
    What also ocurred to me, that the "live" with high refreshing frequency
        is beneficial only when the calculation is expected to take just
        a little time - when the simulation would be run overnight, nobody
        cares so much about getting the data plotted, so we could offer
        a functionality of really only running the script on the background,
        which would do the calculations and then just save the results (csv and jpg).
"""


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
    Callback that is being applied to the simulation to draw data in real
        time about the calculation.
    """
    def __init__(self, Call_at=100.0, plot_limits=[0, 5000, 20, 40], x0=0, ExperimentData=None):
        self.Call_at = Call_at  # specify how often to be called (default is every 50 seccond)
        self.last_call = 0  # placeholder fot time in which the callback was last called
        self.plot_limits = plot_limits  # axis limits to make plot looking "better"
        self.x0 = x0  # x positinon of the temperature we are interested in
        self.TempHistoryAtPoint_x0 = []  # We can be saving data of temperature from specific point in space (x0)
        self.ExperimentData = ExperimentData

    def Call(self, Sim):
        """

        """
        # https://docs.scipy.org/doc/numpy/reference/generated/numpy.interp.html
        self.TempHistoryAtPoint_x0.append(np.interp(self.x0, Sim.x, Sim.T))  # interpolate temperature value at position x0 from point around and save it
        # Update the time calculation is in progress
        app.frames[GraphView].update_elapsed_time()
        if Sim.t[-1] > self.last_call + self.Call_at:  # if it is time to comunicate with GUI then show something

            # Refreshing the graph with all the new time and temperature values
            app.frames[GraphView].refresh_graph_with_new_values(Sim.t[1:], self.TempHistoryAtPoint_x0, self.ExperimentData[0], self.ExperimentData[1])

            print(f"Temperature at x0: {self.TempHistoryAtPoint_x0[-1]} at time {Sim.t[-1]} flux: {Sim.HeatFlux(Sim.t[-1])}")
            self.last_call += self.Call_at

        return True


class HeatTransfer(tk.Tk):
    """
    The core of the GUI, that is handling all other windows and frames.
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

    def show_frame(self, container):
        """
        Displays the chosen container (frame) to the foreground.
        """
        frame = self.frames[container]
        frame.tkraise()


class GraphView(tk.Frame):
    """
    Class that contains the whole main window where the graph is located.
    """
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        # Having access to the current state of the simulation
        # Can be either "running", "paused", "stopped" or "finished"
        self.simulation_state = None

        # Saving the material we are simulating right now
        self.chosen_material = None

        # Saving the beginning of simulation to keep track of time
        # TODO: create logic for the pausing button pausing the time-flow
        self.simulation_started_timestamp = 0

        # Some information to the current release (what is working and what is not)
        info_text = "INFO TEXT: " + \
                    "The Stop button is working now, there are some adjustments needed in the make_sim_step function though"

        self.show_message_text = tk.Text(self, bg="yellow", font=("Calibri", 15), bd=4)
        self.show_message_text.place(relx=0, rely=0, relwidth=1, relheight=0.1)
        self.show_message_text.insert("insert", info_text)

        # Label for some messages to user (errors etc.)
        self.message_to_user = tk.Label(self, fg="red", font=("Calibri", 20))
        self.message_to_user.place(relx=0, rely=0.1, relwidth=1, relheight=0.05)


        # Top frame for the settings etc.
        self.frame_top = tk.Frame(self, bg="#42b6f4", bd=5)
        self.frame_top.place(relx=0.5, rely=0.15, relwidth=0.7, relheight=0.15, anchor="n")

        self.initialize_material_menu(self.frame_top)

        # dt value label and input
        self.dt_value_label = tk.Label(self.frame_top, text="dt value [s]: ")
        self.dt_value_label.place(relx=0, rely=0.3, relheight=0.3, relwidth=0.1)
        self.dt_value_input = tk.Entry(self.frame_top, font=("Calibri", 20))
        self.dt_value_input.place(relx=0.11, rely=0.3, relheight=0.3, relwidth=0.1)
        self.dt_value_input.insert(0, "1.0")

        # Button used to run the simulation
        self.run_button = tk.Button(self.frame_top, text="Run", bg="green", fg="black", bd=2, relief="ridge", font=("Calibri", 20), command=lambda: self.run_button_action())
        self.run_button.place(relx=0.55, rely=0, relheight=1, relwidth=0.15)

        # Button used to pause the simulation
        self.pause_button = tk.Button(self.frame_top, text="Pause", bg="orange", fg="black", bd=2, relief="ridge", font=("Calibri", 20), command=lambda: self.pause_button_action())
        self.pause_button.place(relx=0.7, rely=0, relheight=1, relwidth=0.15)

        # Button used to stop the simulation
        self.stop_button = tk.Button(self.frame_top, text="Stop", bg="red", fg="black", bd=2, relief="ridge", font=("Calibri", 20), command=lambda: self.stop_button_action())
        self.stop_button.place(relx=0.85, rely=0, relheight=1, relwidth=0.15)


        # Label showing the elapsed time during the simulation
        self.elapsed_time_counter = tk.Label(self.frame_top, text="Elapsed time: ")
        self.elapsed_time_counter.place(relx=0, rely=0.7,relheight=0.3, relwidth=0.2)

        # Label showing the error value after the simulation finishes
        self.error_value_placeholder = tk.Label(self.frame_top, text="Error value: ")
        self.error_value_placeholder.place(relx=0.25, rely=0.7,relheight=0.3, relwidth=0.2)


        # Bottom frame for the graph(s)
        self.frame_bottom = tk.Frame(self, bg="#42b6f4", bd=10)
        self.frame_bottom.place(relx=0.5, rely=0.35, relwidth=0.7, relheight=0.6, anchor="n")

        self.initialize_temperature_graph(self.frame_bottom)

    def initialize_material_menu(self, container):
        """
        Renders menu to the screen and fills it with material options.
        """
        self.MATERIAL_DICTIONARY = self.get_materials_from_csv_file()
        self.material_names_list = [key for key in self.MATERIAL_DICTIONARY]

        # Defining the OptionMenu for the choice of material
        self.material_choice = tk.StringVar(container)
        self.material_choice.set(self.material_names_list[0]) # default value

        self.material_label = tk.Label(container, text="Material: ")
        self.material_label.place(relx=0, rely=0, relheight=0.25, relwidth=0.1)
        self.material_menu = ttk.OptionMenu(container, self.material_choice, *self.material_names_list)
        self.material_menu.place(relx=0.11, rely=0, relheight=0.25, relwidth=0.1)

    def initialize_temperature_graph(self, container):
        """
        Renders graph into the window and gives it a template look.
        """
        f = Figure(figsize=(5,5), dpi=100)
        self.a = f.add_subplot(111)
        self.a.set_title("1D Heat Transfer")
        self.a.set_xlabel("Time [s]")
        self.a.set_ylabel("Temperature [°C]")
        self.a.plot([], [])

        self.canvas = FigureCanvasTkAgg(f, container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    def refresh_graph_with_new_values(self, x_values, y_values, x_experiment_values=None, y_experiment_values=None):
        """
        Updates the graph after new values have been calculated.
        TODO: research how the graph could be appended, and not replotted
            from the scratch (which would increase efficiency).
        """
        self.a.cla()

        self.a.set_title("1D Heat Transfer - {}".format(self.chosen_material))
        self.a.set_xlabel("Time [s]")
        self.a.set_ylabel("Temperature [°C]")

        self.a.plot(x_values, y_values, label='Calculated Data')
        if x_experiment_values is not None and y_experiment_values is not None:
            self.a.plot(x_experiment_values, y_experiment_values, label='Experiment Data')

        self.a.legend()
        self.canvas.draw()

    def update_elapsed_time(self):
        """
        Determines how long the simulation has been already running and displays it.
        """
        now = time.time()
        elapsed_time = round(now - self.simulation_started_timestamp, 2)

        self.elapsed_time_counter["text"] = "Elapsed time: {} s".format(elapsed_time)

    def display_error_value(self, error, margin=0.5):
        """
        Displays the numerical error that is the result of calculation.
        If the error is bigger than some margin, then indicate failure with
            red background - otherwise colour it green.
        """
        rounded_error = round(error, 2)
        self.error_value_placeholder["text"] = "Error value: : {}".format(rounded_error)

        if rounded_error < margin:
            self.error_value_placeholder["bg"] = "green"
        else:
            self.error_value_placeholder["bg"] = "red"

    def get_materials_from_csv_file(self):
        """
        Transfers material data from the CSV file into a python dictionary,
            to be able to work with these data.
        Returns:
            (dictionary) Dictionary with keys being material names and values
                         being material properties
        """

        materials_dictionary = {}
        with open("metals_properties.csv", "r") as materials_file:
            csvReader = csv.reader(materials_file)
            next(csvReader, None)  # skip first line (headers)
            for row in csvReader:
                if row:
                    name = row[0]
                    material_properties = {}

                    material_properties["rho"] = row[2]
                    material_properties["cp"] = row[3]
                    material_properties["lmbd"] = row[4]

                    materials_dictionary[name] = material_properties

        return materials_dictionary

    def run_button_action(self):
        """
        Runs the simulation after clicking the Run button. Depending on the
            previous state, it either starts a completely new simulation, or
            continue with the previous one.
        Do not perform any action when the simulation is already running.
        """

        if self.simulation_state == "running":
            return

        # Prepare for the simulation (unless in paused state)
        if self.simulation_state != "paused":
            self.prepare_simulation_with_chosen_material()

        self.simulation_state = "running"
        self.run_button["bd"] = 20
        self.pause_button["bd"] = 2
        self.stop_button["bd"] = 2

        self.make_sim_step()  # enter the Simulation loop

    def pause_button_action(self):
        """
        Pauses the simulation after clicking the Pause button.
        Perform the action only when the simulation is running or stopped.
        """
        if self.simulation_state in ["running", "stopped"]:
            self.simulation_state = "paused"
            self.run_button["bd"] = 2
            self.pause_button["bd"] = 20
            self.stop_button["bd"] = 2

    def stop_button_action(self):
        """
        Stops the simulation after clicking the Stop button.
        Perform the action only when the simulation is running or paused.
        """
        if self.simulation_state in ["running", "paused"]:
            self.simulation_state = "stopped"
            self.run_button["bd"] = 2
            self.pause_button["bd"] = 2
            self.stop_button["bd"] = 20
            self.dt_value_input["state"] = "normal"

    def show_message_to_the_user(self, message):
        """
        Shows a custom message to the user, informing him of some errors or actions
        """
        self.message_to_user["text"] = message

    def prepare_simulation_with_chosen_material(self):
        """
        Determines which material we want to use, prepares all variables
            for the test (resets them), and finally prepares the simulation
        """
        # Determining the chosen material and it's properties
        chosen_material = self.material_choice.get()
        chosen_material_properties = self.MATERIAL_DICTIONARY[chosen_material]

        # Assigning the properties we are interested in
        rho = int(chosen_material_properties["rho"])
        cp = int(chosen_material_properties["cp"])
        lmbd = int(chosen_material_properties["lmbd"])

        # Saving the chosen material to have access to it
        self.chosen_material = chosen_material

        # Reseting all information from previous test
        self.simulation_started_timestamp = time.time()
        self.error_value_placeholder["bg"] = "white"
        self.error_value_placeholder["text"] = "Error value: "

        # Preparing the actual tests with the material data
        self.PrepareSimulation(rho, cp, lmbd)

        return True

    def PrepareSimulation(self, rho, cp, lmbd):
        """
        Defines inputs and initial Simulation state (Sim) for make_sim_step
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
        SteinlessSteel = Material(rho, cp, lmbd)
        self.Sim = Simulation(Length=0.010, Material=SteinlessSteel, N=100, HeatFlux=test_q, AmbientTemperature=T_amb, RobinAlpha=13.5)
        self.MyCallBack = NewCallback(x0=0.00445, plot_limits=[t_data[0], t_data[-1], min(T_data), max(T_data)], ExperimentData=(t_data, T_data))
        self.t_start = t_data[0]
        self.t_stop = t_data[-1]-1
        self.Sim.t.append(0.0)  # push start time into time placeholder inside Simulation class
        self.Sim.T.fill(T_data[0])  # fill initial temperature with value of T0
        self.Sim.T_record.append(self.Sim.T)  # save initial step

        # Getting the dt value from the user input
        # TODO: when value was 2.0, we got "ValueError: A value in x_new is above the interpolation range."
        #   on the self.Sim.T = EvaluateNewStep(self.Sim, self.dt, 0.5) line
        try:
            # Replacing comma with a dot (for those used to writing decimals places with a comma)
            dt_value = self.dt_value_input.get().replace(",", ".")
            self.dt = float(dt_value)
        # If the value is still not parseable to float, make it a default 1.0
        #   and notify the user of it
        except:
            self.dt = 1.0
            self.dt_value_input.delete(0, "end")
            self.dt_value_input.insert(0, "1.0")
            self.show_message_to_the_user("ERROR: Your dt value was not a valid number! We gave it a default of 1 second.")
        # Making the input disbled for changes during the calculation
        self.dt_value_input["state"] = "disabled"

        return True

    def make_sim_step(self):
        """
        Calculates some small amount of steps, before handing control to GUI
            for a while, which will call it again in a short moment.

        TODO: decide, how to handle parameters like dt and max_iter - whether
            to have them as inputs to the function, or instance variables
            - with the lambda function in after() it is possible to input
              parameters into the self-calling function
        """
        if self.Sim.t[-1] >= self.t_stop:
            self.run_button["bd"] = 2
            self.simulation_state = "finished"
            self.dt = None # Setting the value back to undefined, to be udpated the next run
            self.dt_value_input["state"] = "normal" # Allowing to modify the dt input again

            ErrorNorm = np.sum(abs(self.MyCallBack.TempHistoryAtPoint_x0 - self.T_experiment(self.Sim.t[1:])))/len(self.Sim.t[1:])  # average temperature error
            self.display_error_value(ErrorNorm)

        iter = 0
        max_loop_iter = 20
        # enter the loop temporarily and hand the control back to the GUI afterwards
        while self.Sim.t[-1] < self.t_stop and iter <= max_loop_iter:
            self.Sim.T = EvaluateNewStep(self.Sim, self.dt, 0.5)  # evaluate Temperaures at step k
            self.Sim.T_record.append(self.Sim.T)  # push it to designated list
            self.Sim.t.append(self.Sim.t[-1] + self.dt)  # push time step to its list
            self.MyCallBack.Call(self.Sim)
            iter += 1

        if self.simulation_state == "running":
            # https://stackoverflow.com/questions/29158220/tkinter-understanding-mainloop
            # Calls itself after 3ms (this might get it laggy if too low) so other stuff can happen in the app.mainloop in those 3ms
            self.after(1, lambda: self.make_sim_step())

if __name__ == '__main__':
    app = HeatTransfer()

    # https://www.oreilly.com/library/view/python-gui-programming/9781788835886/984b9be2-7c26-445e-9f94-ba8fef208ee0.xhtml
    # Making sure the window is maximized - Platform specific
    if os.name == 'posix':
        app.attributes('-zoomed', True)  # Unix System (X11)
    else:
        app.state("zoomed")  # Windows and MacOS

    app.mainloop()
