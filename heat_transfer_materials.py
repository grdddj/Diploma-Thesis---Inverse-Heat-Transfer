"""
This module is responsible for getting and storing material data.
"""

import os
import sys
import csv
from typing import List, Dict


def resource_path(file_name):
    """
    Helper function allowing for bundling the material data file together
        with the .exe application - so it does not need to be included
        as a "physical" file, and we do not run the danger of somebody
        deleting it.
    NOTE: is not affecting the development process.

    It is not perfect, however, as this file is then read-only, as the data
        can be written there, but they will be erased as soon as the .exe
        application finishes.
        (The reason being the file is stored only in Temp folder, and new
        Temp folder will be created in the next start of the .exe app)

    Args:
        file_name ... name of the file
    """

    # Trying to locate the Temp folder, otherwise using the normal path
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, file_name)


class MaterialService:
    """
    Class holding information about all the available materials
        and their properties
    """

    materials_name_list: List[str] = []
    materials_properties_dict: Dict[str, dict] = {}

    def __init__(self):
        # Defining file with default material data and getting data from there
        default_materials_filename = "metals_properties.csv"
        default_materials_filename = resource_path(default_materials_filename)
        default_materials = self.get_materials_from_csv_file(
            file_name=default_materials_filename, throw_exception=True)

        # Defining filename with custom material data and retrieving its info
        # As we want to access this filename later in saving method,
        #   make it an instance variable
        self.custom_materials_filename = "custom_user_materials.csv"
        custom_materials = self.get_materials_from_csv_file(
            file_name=self.custom_materials_filename)

        # Putting the two dictionaries together
        # Because we supplied custom materials as last, the possible
        #   naming conflicts will be resolved in their favour, so users can
        #   even overwrite default materials
        self.materials_properties_dict = {**default_materials, **custom_materials}

        # Getting the list of all available materials
        self.materials_name_list = [key for key in self.materials_properties_dict]

    @staticmethod
    def get_materials_from_csv_file(file_name: str,
                                    throw_exception: bool = False) -> dict:
        """
        Transfers material data from the CSV file into a python dictionary,
            to be able to work with these data.

        Args:
            file_name ... name of the file
            throw_exception ... whether to throw exception when the file
                will not be found

        Returns:
            (dictionary) Dictionary with keys being material names and values
                         being material properties
        """

        materials_dictionary = {}
        try:
            with open(file_name, "r") as materials_file:
                csv_reader = csv.reader(materials_file)
                next(csv_reader, None)  # skip first line (headers)
                for row in csv_reader:
                    if row:
                        name = row[0]
                        material_properties = {}

                        material_properties["rho"] = float(row[2])
                        material_properties["cp"] = float(row[3])
                        material_properties["lmbd"] = float(row[4])

                        materials_dictionary[name] = material_properties
        except FileNotFoundError:
            print("File not found - {}".format(file_name))
            # Raising exception only when the data is really crucial
            #   and we cannot afford to miss them
            if throw_exception:
                raise

        return materials_dictionary

    def save_custom_user_material(self, material_dict: dict) -> None:
        """
        Including custom user material into its dedicated file
        """

        file_name = self.custom_materials_filename

        # When the custom user file already exists, append it
        # Otherwise create it from scratch
        # Being consistent with the default file, so including the
        #   T_MELT column, and filling it with zero
        if os.path.isfile(file_name):
            with open(file_name, "a") as custom_materials_file:
                csv_writer = csv.writer(custom_materials_file)

                element_row = []
                element_row.append(material_dict["name"])
                element_row.append(0)
                element_row.append(material_dict["properties"]["rho"])
                element_row.append(material_dict["properties"]["cp"])
                element_row.append(material_dict["properties"]["lmbd"])
                csv_writer.writerow(element_row)
        else:
            with open(file_name, "w") as custom_materials_file:
                csv_writer = csv.writer(custom_materials_file)

                headers = ["NAME", "T_MELT [C]", "RHO [kg/m3]",
                           "C_P [J/(kg*K)]", "LAMBDA [W/(m*K)]"]
                csv_writer.writerow(headers)

                element_row = []
                element_row.append(material_dict["name"])
                element_row.append(0)
                element_row.append(material_dict["properties"]["rho"])
                element_row.append(material_dict["properties"]["cp"])
                element_row.append(material_dict["properties"]["lmbd"])
                csv_writer.writerow(element_row)
