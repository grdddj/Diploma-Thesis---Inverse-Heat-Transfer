import csv

class Material:
    def __init__(self, rho, cp, lmbd):
        self.rho = rho  # Mass density
        self.cp = cp  # Specific heat capacity
        self.lmbd = lmbd  # Heat conductivity

class ExperimentalData:
    def __init__(self, csv_file_path="DATA.csv"):
        self.t_data = []  # experimental data of time points
        self.T_data = []  # experimental data of temperature
        self.q_data = []  # experimental data of Measured HeatFluxes (might be missing)
        self.T_amb_data = []  # experimental data of ambient temperature
        with open(csv_file_path) as csvDataFile:
            csvReader = csv.reader(csvDataFile)
            next(csvReader, None)  # skip first line (headers)
            row = next(csvReader)  # read first line
            self.t_data.append(float(row[0]))
            self.T_data.append(float(row[1]))
            self.q_data.append(float(row[2]))
            self.T_amb_data.append(float(row[3]))
            self.Mat = Material(float(row[4]),float(row[5]),float(row[6]))
            self.Length = float(row[7])
            self.x0 = float(row[8])
            self.RobinAlpha = float(row[9])
            for row in csvReader:
                self.t_data.append(float(row[0]))
                self.T_data.append(float(row[1]))
                self.q_data.append(float(row[2]))
                self.T_amb_data.append(float(row[3]))

    # TODO: define how to handle missing data (like HeatFlux) in the csv
