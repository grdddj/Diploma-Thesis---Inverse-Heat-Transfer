"""
This script is fetching chosen properties of specified
chemical elements and saving them locally in the form of CSV file.

It starts at the Wikipedia page with the list of all the chemical elements,
loops through them all, visits their dedicated page and draws information
that we want, mainly from the right-side info table.

It is possible to filter these elements at will, right now we include only
metals, all imaginable filters can be included easily
(f.e. atomic number > 20, density < 3000...).

Notice the big amount of try/except blocks, that all do the same thing -
in any exception they skip out current element - therefore this could be all
done in just one block, but this layout leaves room for future custom
error-handling of each possible exception.
"""
# Imports for fetching and analysing the content from web
# bs4 is not a native module, need to install it
import requests
from bs4 import BeautifulSoup
import re
from csv import writer
import json

# CONTROLLERS
custom_file_name = "metals_properties"

def main():
    # Initial page, from which we get the list of all elements
    initial_page = "https://en.wikipedia.org/wiki/List_of_chemical_elements"

    # Loading the initial_page
    initial_response = requests.get(initial_page)
    initial_soup = BeautifulSoup(initial_response.text, "html.parser")

    # Extracting the list of all the elements (all the individual rows)
    all_elements = initial_soup.find("table", class_="wikitable").find("tbody").findAll("tr")

    # Preparing a variable to store all the elements
    element_list = []

    # Loop through all the elements, analyse them and gather data
    for element in all_elements:
        try:
            element_name = element.findAll("td")[2].get_text().strip()
            # Locating the link of individual element
            element_page = "https://en.wikipedia.org" + element.findAll("td")[2].find("a")["href"]

            # Loading the element_link
            element_response = requests.get(element_page)
            element_soup = BeautifulSoup(element_response.text, "html.parser")

            # Locating the right-side table with info
            element_info = element_soup.find(class_="infobox").findAll("tr")
        except Exception as e:
            # In the case of some error just continue with next element
            continue

        # Execute filtering of elements that we want
        # In this case we are interested only in metals
        categories = ""
        for row in element_info:
            try:
                # It is strange, but "Element category" sometimes changes to something else
                if row.find("th").find("a")["title"] in ["Element category", "Names for sets of chemical elements"]:
                    categories = row.find("td").get_text().strip()
                    break
            except Exception as e:
                continue

        # If we do not encounter the word "metal", then do not include this element
        # We must include word boundaries ("\b"), because there is "nonmetal" category
        if re.search(r"\b(metal)\b", categories, flags=re.IGNORECASE) is None:
            print("Not included: " + element_name)
            continue
        else:
            print("Included element: " + element_name)

        # Preparing the variables for storing fetched information
        # Some of them we just fetch and process, some of them need to be calculated
        element_density = element_melting_temp = 0
        element_thermal_conductivity = element_thermal_capacity = 0

        # Thermal capacity must be taken from the overview
        try:
            element_thermal_capacity = element.findAll("td")[-3].get_text().strip()
        except Exception as e:
            continue

        # Looking for the fields of our interest and storing the info
        for row in element_info:
            try:
                if row.find("th").find("a")["title"] == "Melting point":
                    element_melting_temp = row.find("td").get_text().strip()
                    continue
                if row.find("th").find("a")["title"] == "Density":
                    element_density = row.find("td").get_text().strip()
                    continue
                if row.find("th").find("a")["title"] == "Thermal conductivity":
                    element_thermal_conductivity = row.find("td").get_text().strip()
                    continue
            except Exception as e:
                continue

        # Formatting the fetched info (usually to integers)
        # If we fail in anything, do not include the element, not to have corrupt data
        try:
            element_melting_temp = take_first_numbers(element_melting_temp)
            element_melting_temp = int(float(element_melting_temp))

            element_density = take_first_numbers(element_density)
            element_density = int(float(element_density)*1000)

            element_thermal_conductivity = take_first_numbers(element_thermal_conductivity)
            element_thermal_conductivity = int(float(element_thermal_conductivity))

            element_thermal_capacity = int(float(element_thermal_capacity)*1000)
        except Exception as e:
            continue

        try:
            element_details = {
                "element_name": element_name,
                "element_melting_temp": element_melting_temp,
                "element_density": element_density,
                "element_thermal_capacity": element_thermal_capacity,
                "element_thermal_conductivity": element_thermal_conductivity,
            }
            element_list.append(element_details)
        except Exception as e:
            continue

    # Printing the whole output to the terminal as well
    print(json.dumps(element_list, indent=4))

    # Saving the output as an CSV file
    try:
        file_name = custom_file_name if custom_file_name != "" else "elements"
        with open(file_name + ".csv", "w") as csv_file:
        	csv_writer = writer(csv_file)
        	headers = ["NAME", "T_MELT [°C]", "RHO [kg/m3]", "C_P [J/(kg*K)]", "LAMBDA [W/(m*K)]"]
        	csv_writer.writerow(headers)

        	for element in element_list:
        		element_row = []
        		element_row.append(element["element_name"])
        		element_row.append(element["element_melting_temp"])
        		element_row.append(element["element_density"])
        		element_row.append(element["element_thermal_capacity"])
        		element_row.append(element["element_thermal_conductivity"])
        		csv_writer.writerow(element_row)
    except Exception as e:
        pass

def take_first_numbers(string: str):
    """
    Processes a string that is beginning with a number, takes only the
    part from the beginning until the end of the number, and returns it
    """
    number = ""
    for char in string:
        if re.search("[0-9.]", char) is not None:
            number = number + char
        else:
            return number
    return number

if __name__ == '__main__':
    main()
