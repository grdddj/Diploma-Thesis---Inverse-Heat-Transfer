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
            csvReader = csv.DictReader(csvDataFile)
            next(csvReader, None)  # skip first line (headers)
            for row in csvReader:
                self.t_data.append(float(row.get("Time", 0)))
                self.T_data.append(float(row.get("Temperature", 0)))
                self.q_data.append(float(row.get("HeatFlux", 0)))
                self.T_amb_data.append(float(row.get("T_amb", 0)))

    # TODO: define how to handle missing data (like HeatFlux) in the csv
