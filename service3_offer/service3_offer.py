from flask import Flask, request, jsonify
from datetime import datetime
import os

app = Flask(__name__)

OUTPUT_DIR = "/app/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_offer_letter(customer):
    current_date = datetime.now().strftime("%Y-%m-%d")

    return f"""Date: {current_date}
{customer['FIRST_NAME']} {customer['LAST_NAME']}
{customer['STREET_ADDRESS']}
{customer['CITY']}, {customer['POSTAL_CODE']}
{customer['COUNTRY']}
Account Number: {customer['ACCOUNT_NUMBER']}

Dear {customer['FIRST_NAME']} {customer['LAST_NAME']},

As a valued customer, we are pleased to offer you a special financial product designed to
support your needs.

You have been pre-approved for the following offer:
Product Type: {customer['OFFER_TYPE']}
Credit Limit: ${customer['CREDIT_LIMIT']}

This offer is available exclusively to customers with accounts like yours (Account Number:
{customer['ACCOUNT_NUMBER']}).

If you would like to accept this offer or learn more, please contact us or visit your nearest
branch.

We appreciate your continued trust in our bank.

Sincerely,
Customer Relations Team
Your Bank Name
"""

@app.route("/generate", methods=["POST"])
def generate_offer_letters():
    data = request.get_json()
    customers = data.get("customers", [])
    generated_files = []

    for customer in customers:
        if customer.get("LETTER_TYPE", "").strip().lower() != "offer":
            continue

        if not customer.get("OFFER_TYPE") or not customer.get("CREDIT_LIMIT"):
            continue

        letter_text = create_offer_letter(customer)

        filename = f"offer_{customer['FIRST_NAME']}_{customer['LAST_NAME']}.txt"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(letter_text)

        generated_files.append(filename)

    return jsonify({
        "status": "success",
        "generated_count": len(generated_files),
        "files": generated_files
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "offer-letter"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)