import csv


class ExperimentDataCannotBeParsedError(Exception):
    """
    Defining custom exception type that will be thrown when something fails here
    """

    def __init__(self, msg: str = "ERROR"):
        self.message = msg

    def __str__(self):
        """
        Defines what to show when exception is printed - giving some useful info
        """

        return """
                Experiment data cannot be processed. Please take a look at them.
                Column names should be:
                    - Time
                    - Temperature
                    - HeatFlux
                    - T_amb

                Issue: {}
                """.format(self.message)


class Material:
    """
    Class responsible for initializing and storing material data
    """

    def __init__(self, rho, cp, lmbd):
        self.rho = rho  # Mass density
        self.cp = cp  # Specific heat capacity
        self.lmbd = lmbd  # Heat conductivity


class ExperimentalData:
    """
    Class responsible for initializing and storing experimental data

    TODO: really agree on the parsing logic (indexes vs named columns)
    """

    def __init__(self, csv_file_path="DATA.csv"):
        # Preparing lists for storing all the data
        self.t_data = []  # experimental data of time points
        self.T_data = []  # experimental data of temperature
        self.q_data = []  # experimental data of Measured HeatFluxes (might be missing)
        self.T_amb_data = []  # experimental data of ambient temperature

        # Defining the column names we are expecting
        self.t_column_name = "Time"
        self.T_column_name = "Temperature"
        self.q_column_name = "HeatFlux"
        self.T_amb_column_name = "T_amb"

        # Trying to parse the file with experimental data, in case of any error
        #   relay it with our custom name
        try:
            with open(csv_file_path) as csv_file:
                # NOTE: when using DictReader, skipping first row is not necessary,
                #   on the contrary, we would be losing one row of data by it
                csv_reader = csv.DictReader(csv_file)

                # Validating the correctness of CSV file
                self.check_CSV_file_correctness(csv_reader.fieldnames)

                # Filling the data row by row
                for row in csv_reader:
                    self.t_data.append(float(row.get(self.t_column_name, 0)))
                    self.T_data.append(float(row.get(self.T_column_name, 0)))
                    self.q_data.append(float(row.get(self.q_column_name, 0)))
                    self.T_amb_data.append(float(row.get(self.T_amb_column_name, 0)))
        except ExperimentDataCannotBeParsedError:
            raise
        except Exception as e:
            raise ExperimentDataCannotBeParsedError(e)

    def check_CSV_file_correctness(self, column_names: list) -> None:
        """
        Making sure the CSV file contains the right columns.
        We need the time and ambient temperatures to be there all the time,
          and them at least one of the temperature and flux.
        In case of some problem throw our custom error.

        Args:
            column_names ... list of columns from the CSV file
        """

        if self.t_column_name not in column_names:
            msg = "Time data is empty, please use 'Time' column for this data"
            raise ExperimentDataCannotBeParsedError(msg)
        if self.T_amb_column_name not in column_names:
            msg = "Ambient temperature data is empty, please use 'T_amb' column for this data"
            raise ExperimentDataCannotBeParsedError(msg)
        if self.T_column_name not in column_names and self.q_column_name not in column_names:
            msg = "Temperature and flux data are empty, please use 'Temperature' and 'HeatFlux' columns for this data"
            raise ExperimentDataCannotBeParsedError(msg)
