import re
import csv
import os

# def clean_bank_lines(text):
#     cleaned_lines = []

#     for line in text.strip().splitlines():
#         # Remove leading special characters like =, :, ; etc.
#         cleaned_line = re.sub(r'^[^0-9A-Za-z]+', '', line).strip()

#         if cleaned_line:  # skip empty lines
#             cleaned_lines.append(cleaned_line)

#     return cleaned_lines

# def clean_bank_lines(text):
#     cleaned_lines = []
#     date_pattern = re.compile(r'^\d{2}-[A-Za-z]{3}-\d{4}')

#     for line in text.strip().splitlines():
#         # Remove leading special characters like =, :, ; etc.
#         cleaned_line = re.sub(r'^[^0-9A-Za-z]+', '', line).strip()

#         # Only keep lines that start with a valid date pattern
#         if date_pattern.match(cleaned_line):
#             cleaned_lines.append(cleaned_line)

#     return cleaned_lines



def clean_bank_statement(lines):
    cleaned_data = []

    for line in lines:
        # Remove leading characters that aren't part of the date
        parts = line.split()
        if not parts[0][0].isdigit() and len(parts) > 1:
            line = ' '.join(parts[1:])

        # Fix number formatting issues
        # First, handle the case where there's a space after a number instead of a decimal point
        if ' 00' in line:
            line = line.replace(' 00', '.00')

        # Fix incorrect characters in decimal places
        words = line.split()
        if len(words) > 0:
            last_word = words[-1]
            if '.' in last_word:
                decimal_parts = last_word.split('.')
                if len(decimal_parts) == 2 and not decimal_parts[1].isdigit():
                    # Replace non-digit characters with digits (assuming they should be zeros)
                    new_decimal = ''.join(['0' if not c.isdigit() else c for c in decimal_parts[1]])
                    words[-1] = decimal_parts[0] + '.' + new_decimal
                    line = ' '.join(words)

        cleaned_data.append(line)

    return cleaned_data

def process_and_validate_bank_statement(result, output_file="validated_bank_statement.csv"):
    """
    Process raw bank statement data, extract transaction details, and validate the transactions
    by checking if the balance after each transaction matches the expected balance.

    Args:
        result (list): List of raw bank statement lines
        output_file (str): Path to the output CSV file

    Returns:
        str: Path to the output CSV file
    """
    # Define the output headers in the specified order
    output_headers = ['Date', 'Description', 'Type', 'Label', 'Amount', 'Balance', 'Status']

    # First pass: Extract transaction details from raw data
    transactions = []
    previous_balance = None

    for i, line in enumerate(result):
        # Extract date (assuming it's always at the beginning and in DD-MMM-YYYY format)
        date_match = re.match(r'(\d{2}-[A-Za-z]{3}-\d{4})', line)
        date = date_match.group(1) if date_match else ""

        # Remove the date from the line
        remaining = line[len(date):].strip() if date else line

        # First, extract the balance which is always the last number pattern in the line
        # Modified regex to handle both complete numbers with decimals and incomplete numbers
        balance_match = re.search(r'(-?[\d,]+(?:\s+[\d,]+)*(?:\.\d+)?)$', remaining)
        balance = balance_match.group(1) if balance_match else ""

        # Remove the balance from the remaining text
        if balance:
            # Use the exact balance string to remove it from the remaining text
            remaining = remaining[:remaining.rfind(balance)].strip()

        # Now extract the amount which should be the last number pattern in the remaining text
        # Modified regex to handle both complete numbers with decimals
        amount_match = re.search(r'(-?[\d,]+\.\d+)(?:\s*)$', remaining)
        amount = amount_match.group(1) if amount_match else ""

        # Remove the amount from the remaining text
        if amount:
            # Use the exact amount string to remove it from the remaining text
            remaining = remaining[:remaining.rfind(amount)].strip()

        # Clean up the description - remove numbers and special characters
        description = re.sub(r'[^a-zA-Z\s]', '', remaining).strip()
        # Remove extra spaces
        description = re.sub(r'\s+', ' ', description)

        # Fix the balance format by removing internal spaces and commas
        balance_for_calc = balance.replace(" ", "").replace(",", "")

        # Add decimal zeros if missing (e.g., "-1,449" becomes "-1449.00")
        if balance_for_calc and '.' not in balance_for_calc:
            balance_for_calc = balance_for_calc + ".00"

        # Remove commas from amount
        amount_for_output = amount.replace(",", "")

        # Convert amount and balance to float for comparison
        amount_value = float(amount.replace(',', '')) if amount else 0

        try:
            balance_value = float(balance_for_calc) if balance_for_calc else 0
        except ValueError:
            print(f"Warning: Could not convert balance '{balance_for_calc}' to float. Using 0.")
            balance_value = 0

        # Determine if it's a debit or credit transaction
        if i == 0 or previous_balance is None:
            # First transaction is typically a debit (loan disbursement)
            transaction_type = '##'  # Debit
            label = 'Debit'
        else:
            # Compare current balance with previous balance
            if balance_value < previous_balance:
                transaction_type = '##'  # Debit (balance decreased)
                label = 'Debit'
            else:
                transaction_type = '*'   # Credit (balance increased)
                label = 'Credit'

        # Create transaction record
        transaction = {
            'Date': date,
            'Description': description,
            'Type': transaction_type,
            'Label': label,
            'Amount': amount_for_output,
            'Balance': balance_for_calc
        }

        transactions.append(transaction)

        # Update previous_balance for next comparison
        previous_balance = balance_value

    # Second pass: Validate transactions
    current_balance = 0.00
    validated_transactions = []

    for record in transactions:
        # Convert string values to appropriate types
        amount = float(record["Amount"]) if record["Amount"] else 0.00
        balance = float(record["Balance"]) if record["Balance"] else 0.00
        txn_type = record["Type"]

        # Calculate expected balance
        expected_balance = current_balance

        if txn_type == "##":  # Debit
            expected_balance -= amount
        elif txn_type == "*":  # Credit
            expected_balance += amount
        else:
            record["Status"] = "❓ Unknown Type"
            validated_transactions.append(record)
            continue

        # Compare expected vs actual balance (rounding to avoid float precision issues)
        if round(expected_balance, 2) == round(balance, 2):
            record["Status"] = "✅ OK"
        else:
            record["Status"] = f"❌ FALSE (Expected: {round(expected_balance, 2)})"

        # Update the balance for the next iteration using the *actual* balance
        current_balance = balance

        validated_transactions.append(record)

    # Write the validated data to the output CSV file
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=output_headers)
        writer.writeheader()
        writer.writerows(validated_transactions)

    print(f"Processing and validation complete. Output saved to: {os.path.abspath(output_file)}")
    return output_file
