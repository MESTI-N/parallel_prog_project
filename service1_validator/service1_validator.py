import json
import re
import logging
from datetime import datetime

import requests
from flask import Flask, jsonify

# Initialize Flask app and logging
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Path to the customer data file
DATA_PATH = "/app/data/customers.json"

# URLs for the other services
WELCOME_SERVICE_URL = "http://welcome-letter:5002/generate"
OFFER_SERVICE_URL = "http://offer-letter:5003/generate"

# Validate a single customer record
def validate_record(record):
    # Initialize an empty list to store validation errors
    errors = []

    # Check if the first name is missing or empty
    if not record.get("FIRST_NAME", "").strip():
        errors.append("FIRST_NAME is missing or empty")

    # Check if the last name is missing or empty
    if not record.get("LAST_NAME", "").strip():
        errors.append("LAST_NAME is missing or empty")

    # Get the account number and check if its missing or empty
    account = record.get("ACCOUNT_NUMBER", "").strip()
    if not account:
        errors.append("ACCOUNT_NUMBER is missing or empty")
    # Check if the account number is between 8-16 digits
    elif not re.fullmatch(r"\d{8,16}", account):
        errors.append("ACCOUNT_NUMBER must be 8-16 digits")

    # Check if the street address is missing or empty
    if not record.get("STREET_ADDRESS", "").strip():
        errors.append("STREET_ADDRESS is missing or empty")

    # Check if the city is missing or empty
    if not record.get("CITY", "").strip():
        errors.append("CITY is missing or empty")

    # Check if the postal code is missing or empty
    if not record.get("POSTAL_CODE", "").strip():
        errors.append("POSTAL_CODE is missing or empty")

    # Check if the country is missing or empty
    if not record.get("COUNTRY", "").strip():
        errors.append("COUNTRY is missing or empty")

    # Get the letter type and check if its missing or empty
    letter_type = record.get("LETTER_TYPE", "").strip().lower()
    # Check if the letter type is either "welcome" or "offer"
    if letter_type not in ("welcome", "offer"):
        errors.append("LETTER_TYPE must be 'welcome' or 'offer'")

    # If the letter type is offer, check if the offer type is either Credit Card or Line of Credit
    if letter_type == "offer":
        offer_type = record.get("OFFER_TYPE", "").strip()
        if offer_type not in ("Credit Card", "Line of Credit"):
            errors.append("OFFER_TYPE must be 'Credit Card' or 'Line of Credit' for offer letters")

        # Check if the credit limit is missing or empty
        credit_limit = record.get("CREDIT_LIMIT", "").strip()
        if not credit_limit:
            errors.append("CREDIT_LIMIT is required for offer letters")
        else:
            # Check if the credit limit is a valid number
            try:
                limit_val = float(credit_limit)
                if limit_val <= 0:
                    errors.append("CREDIT_LIMIT must be a positive number")
            # If the credit limit is not a valid number, add an error
            except ValueError:
                errors.append("CREDIT_LIMIT must be a valid number")
    # If there are no errors, the record is valid
    is_valid = len(errors) == 0
    return is_valid, errors

# Trigger other services with the validated records
def trigger_service(url, records, service_name):
    # If there are no records, return True
    if not records:
        return True

    try:
        # Send the records to the other service
        resp = requests.post(url, json={"customers": records}, timeout=10)
        # If the response is not successful, raise an error
        resp.raise_for_status()
        # Log the successful trigger
        app.logger.info(
            "Triggered %s with %d records - response: %s",
            service_name, len(records), resp.json(),
        )
        return True
    # If the connection to the other service fails, log a warning and return False
    except requests.exceptions.ConnectionError:
        app.logger.warning(
            "%s is not reachable at %s (service may not be running yet)",
            service_name, url,
        )
        return False
    # If there is an error, log it and return False
    except Exception as exc:
        app.logger.error("Error triggering %s: %s", service_name, exc)
        return False

# Validate the customer data endpoint
@app.route("/validate", methods=["POST"])
def validate():
    # Try to open the customer data file
    try:
        # Open the customer data file
        with open(DATA_PATH, "r") as f:
            # Load the customer data
            customers = json.load(f)
    # If the file is not found, return a 404 error
    except FileNotFoundError:
        return jsonify({"error": f"Data file not found at {DATA_PATH}"}), 404
    # If the JSON is invalid, return a 400 error
    except json.JSONDecodeError as exc:
        return jsonify({"error": f"Invalid JSON in data file: {exc}"}), 400

    # Initialize lists to store the records for each service
    welcome_records = []
    offer_records = []
    # Initialize counters for the number of valid and invalid records
    valid_count = 0
    invalid_count = 0

    # Validate each record
    for record in customers:
        # Validate the record
        is_valid, errors = validate_record(record)
        # If the record is valid, add it to the list of valid records
        if is_valid:
            record["status"] = "valid"
            record["errors"] = []
            valid_count += 1
            # Get the letter type and add the record to the list of records for the corresponding service
            letter_type = record["LETTER_TYPE"].strip().lower()
            if letter_type == "welcome":
                welcome_records.append(record)
            elif letter_type == "offer":
                offer_records.append(record)
        else:
            record["status"] = "invalid"
            record["errors"] = errors
            invalid_count += 1
    # Write the updated customer data back to the file
    with open(DATA_PATH, "w") as f:
        json.dump(customers, f, indent=2)
    # Log the validation results
    app.logger.info(
        "Validation complete - %d valid, %d invalid out of %d total",
        valid_count, invalid_count, len(customers),
    )

    # Trigger the welcome letter service with the valid welcome records
    welcome_triggered = trigger_service(WELCOME_SERVICE_URL, welcome_records, "Welcome Letter Service")
    # Trigger the offer letter service with the valid offer records
    offer_triggered = trigger_service(OFFER_SERVICE_URL, offer_records, "Offer Letter Service")

    # Return the validation results
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "total_records": len(customers),
        "valid": valid_count,
        "invalid": invalid_count,
        "welcome_triggered": welcome_triggered,
        "welcome_count": len(welcome_records),
        "offer_triggered": offer_triggered,
        "offer_count": len(offer_records),
        "results": customers,
    })

# Health check endpoint
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "validator"})

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
