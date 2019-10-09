"""
This module is responsible for getting and storing material data.
"""

import csv

class MaterialService:
    materials_name_list = []
    materials_properties_dict = {}

    def __init__(self):
        self.materials_properties_dict = self.get_materials_from_csv_file()
        self.materials_name_list = [key for key in self.materials_properties_dict]

    def get_materials_from_csv_file(self):
        """
        Transfers material data from the CSV file into a python dictionary,
            to be able to work with these data.
        Returns:
            (dictionary) Dictionary with keys being material names and values
                         being material properties
        """

        materials_dictionary = {}
        # TODO: add some error handling
        with open("metals_properties.csv", "r") as materials_file:
            csvReader = csv.reader(materials_file)
            next(csvReader, None)  # skip first line (headers)
            for row in csvReader:
                if row:
                    name = row[0]
                    material_properties = {}

                    material_properties["rho"] = int(row[2])
                    material_properties["cp"] = int(row[3])
                    material_properties["lmbd"] = int(row[4])

                    materials_dictionary[name] = material_properties

        return materials_dictionary
