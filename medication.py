import requests
import argparse
from bs4 import BeautifulSoup
import pandas as pd  # Import pandas
import re
import sys

class SystmOnline:
    """
    A class to interact with the SystmOnline platform, enabling users to login, 
    query medications, and request prescriptions.
    """
    
    BASE_URL = "https://systmonline.tpp-uk.com"

    def __init__(self, username: str, password: str):
        """
        Initializes the SystmOnline instance with user credentials.
        
        :param username: The username for login
        :param password: The password for login
        """
        self.ENDPOINT = self.BASE_URL
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.soup = None

    def login(self) -> tuple:
        """
        Logs into the SystmOnline portal.
        
        :return: A tuple containing a success flag (bool) and an error message (str) if applicable.
        """
        payload = {
            "Username": self.username,
            "Password": self.password,
            "Login": ""
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": "CookieTest=CookieTest"
        }
        
        response = self.session.post(f"{self.ENDPOINT}/2/Login", data=payload, headers=headers)
        self.soup = BeautifulSoup(response.text, "html.parser")
        
        error_span = self.soup.find("span", {"id": "errorText"})
        
        if error_span:
            return False, error_span.text.strip()
        elif "MainMenu" in response.url:
            return True, ""
        else:
            return False, "Login status unknown. Check the response."

    def extract_form_data(self, action: str) -> dict:
        """
        Extracts hidden form data required for POST requests.
    
        :param action: The action attribute of the form to be extracted.
        :return: A dictionary of form field names and values.
                 If multiple fields share the same name, values are stored in a list.
        """
        form = self.soup.find("form", {"method": "POST", "action": action})
        if not form:
            return None

        form_data = {}
        for input_tag in form.find_all("input", {"type": "HIDDEN"}):
            name = input_tag.get("name")
            value = input_tag.get("value", "")

            if name in form_data:
                # Convert existing value into a list if it isn't already
                if not isinstance(form_data[name], list):
                    form_data[name] = [form_data[name]]
                form_data[name].append(value)
            else:
                form_data[name] = value

        return form_data

    def query_medications(self, order_medications: bool = False, order_all: bool = False):
        """
        Queries the medication list and optionally orders medications.
        
        :param order_medications: Whether to proceed with ordering medications.
        :param order_all: Whether to order all medications automatically.
        """
        post_data = self.extract_form_data("Medication")
        if not post_data:
            print("Error: Unable to retrieve medication data.")
            return
        
        response = self.session.post(f"{self.BASE_URL}/2/Medication", data=post_data)
        self.soup = BeautifulSoup(response.text, "html.parser")
        medications = []

        for row in self.soup.find_all("tr")[1:]:
            columns = row.find_all("td")
            if len(columns) < 2:
                continue

            checkbox = row.find("input", {"type": "CHECKBOX"})
            can_order = "Yes" if checkbox else "No"
            med_id = checkbox["value"] if checkbox else None
            drug_name_tag = columns[1].find("h3")

            if drug_name_tag:
                drug_name = drug_name_tag.text.strip()
                details = columns[1].get_text("\n", strip=True).replace(drug_name, "")
                last_issued = re.search(r"Last Issued:\s*(\d{1,2}\s[A-Za-z]{3}\s\d{4})", details)
                last_requested = re.search(r"Last requested\s*(\d{1,2}\s[A-Za-z]{3}\s\d{2})", details)
                
                medications.append([med_id, drug_name, last_issued.group(1) if last_issued else "", last_requested.group(1) if last_requested else "", can_order])

        self.display_medications(medications, order_medications, order_all)

    def display_medications(self, medications: list, order_medications: bool, order_all: bool):
        """
        Displays the list of medications and handles ordering logic.
        
        :param medications: A list of medications with details.
        :param order_medications: Whether to proceed with ordering.
        :param order_all: Whether to order all available medications.
        """
        if not medications:

            print("No medications found.")
            return

        df = pd.DataFrame(medications, columns=["ID", "Drug Name", "Last Issued", "Last Requested", "Can Be Ordered"])
        pd.set_option("display.max_colwidth", None)

        if order_medications:
            df = df[df["Can Be Ordered"] == "Yes"]

            if df.empty:
                print("No medications available for ordering.")
                return

            # Reset ids to 1
            df = df.reset_index(drop=True)
            df.index = df.index + 1
            print(df[["Drug Name", "Last Issued", "Last Requested", "Can Be Ordered"]])

            selected_ids = df["ID"].tolist() if order_all else self.prompt_order_medications(df)
            self.order_medications(selected_ids)
        
        else:
            df.index = df.index + 1
            print(df[["Drug Name", "Last Issued", "Last Requested", "Can Be Ordered"]])

    def prompt_order_medications(self, df: pd.DataFrame) -> list:
        """
        Prompts the user to select medications to order.
        
        :param df: DataFrame containing medication details.
        :return: A list of selected medication IDs.
        """
        try:
            user_input = input("\nEnter the medication indices to order (comma separated, e.g. 1,2,5): ")
            selected_indices = [(int(x.strip())-1) for x in user_input.split(",")]
            ordered_medications = df.iloc[selected_indices].reset_index(drop=True)
            print("\nOrdered medications:", ", ".join(ordered_medications["Drug Name"].tolist()))
            return ordered_medications["ID"].tolist()
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")
            return []

    def order_medications(self, med_ids: list):
        """
        Submits medication order requests.
        
        :param med_ids: A list of medication IDs to be ordered.
        """
        if not med_ids:
            print("No medications selected for ordering.")
            return
        
        # Request medication
        post_data = self.extract_form_data("RequestMedication")
        if not post_data:
            print("Error: Unable to retrieve request form.")
            return

        post_data.update({"Drug": med_ids, "MedRequestType": "Request existing medication"})
        response = self.session.post(f"{self.BASE_URL}/2/RequestMedication", data=post_data)
        self.soup = BeautifulSoup(response.text, "html.parser")

        # Confirm medication
        post_data = self.extract_form_data("RequestMedication")

        if not post_data:
            print("Error: Unable to retrieve request form.")
            return

        # Send request
        response = self.session.post(f"{self.BASE_URL}/2/RequestMedication", data=post_data)
        print("Medication request submitted successfully." if response.ok else "Error submitting medication request.")

# Parse command-line arguments
def parse_arguments():
    """
    Parses command-line arguments for the SystmOnline Medication Fetcher.
    
    :return: An ArgumentParser object with configured arguments.
    """
    parser = argparse.ArgumentParser(description="SystmOnline Medication Fetcher")
    parser.add_argument("--username", type=str, required=True, help="Username for login")
    parser.add_argument("--password", type=str, required=True, help="Password for login")
    parser.add_argument("--medications", action="store_true", help="Query medications")
    parser.add_argument("--order-medications", action="store_true", help="Order specific medications")
    parser.add_argument("--all", action="store_true", help="Order all medications when combined with --order-medications")
    return parser

# Main execution logic
if __name__ == "__main__":

    args = parse_arguments().parse_args()

    if not args.medications and not args.order_medications:
        parse_arguments().print_help()
        sys.exit(1)

    systm_online = SystmOnline(args.username, args.password)
    success, message = systm_online.login()
    if not success:
        print(f"Error: {message}")
        sys.exit(1)

    systm_online.query_medications(order_medications=args.order_medications, order_all=args.all)
