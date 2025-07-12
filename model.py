# import time
# import torch
# from ocr_2 import ocr_pdf_to_text  # Make sure ocr.py is in the same directory or in PYTHONPATH

# from transformers import AutoTokenizer, AutoModelForCausalLM

# # # Load the Gemma 2B instruction-tuned model and tokenizer
# # model_name = "mistralai/Mistral-7B-v0.1"
# # tokenizer = AutoTokenizer.from_pretrained(model_name)
# # model = AutoModelForCausalLM.from_pretrained(
# #     model_name,
# #     torch_dtype=torch.bfloat16,
# #     device_map="auto"
# # )

# model_path = "mistral"  # or full path like r"C:\models\mistral"

# model = AutoModelForCausalLM.from_pretrained(
#     model_path,
#     torch_dtype=torch.float32  # use float32 on CPU
# ).to("cpu")

# tokenizer = AutoTokenizer.from_pretrained(model_path)


# start_time = time.time()
# print("Processing Starts...")

# # Build the prompt with an example
# def build_prompt(ocr_text):
#     return f"""You are a helpful assistant. Your task is to extract only the lines that represent financial transactions from the OCR bank statement text. These include debits, credits, interest payments, loan disbursements, recoveries, etc.

# Return only the transaction lines exactly as they appear, without explanation or extra formatting.

# NOTE: EACH TRANSACTION LINE MUST START WITH A DATE IN THE FORMAT DD-MMM-YYYY (e.g., 09-Apr-2023). ALSO BEFORE THE DATE THERE CAN APPEAR SOME EXTRA SYMBOLS LIKE =, ;, :, =!

# Here are some examples of a valid transaction line:

# 09-Apr-2023 2004204258873001 Loan Disbursement Debit 2,000,000.00 -2,000,000.00
# ; 09-Aug-2023 6042588730002 Penal Int 58.35 -1,810,963.63
# = 09-May-2023 Loan Recovery From -2004204258873007 82,104.00 -1,332 896.00
# : 08-Jun-2023 Loan Recovery From -2004204258873001 82,104.00 -1,865,288.72

# An invalid transaction line would be:

# RAHMAN ELECTRIC AND HARDWARE Cust ID 04258873

# Now extract transaction lines from this text:

# {ocr_text}

# Transaction lines:"""

# # Generate response from LLM
# def extract_transactions(text):
#     prompt = build_prompt(text)
#     inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

#     with torch.no_grad():
#         output = model.generate(
#             **inputs,
#             max_new_tokens=1500,
#             temperature=0.2,
#             do_sample=False,
#             pad_token_id=tokenizer.eos_token_id
#         )

#     decoded = tokenizer.decode(output[0], skip_special_tokens=True)

#     # Extract only the transaction lines
#     if "Transaction lines:" in decoded:
#         return decoded.split("Transaction lines:")[-1].strip()
#     return decoded.strip()


# # Step 1: Get raw text from OCR function
# pdf_path = "Brac 1.pdf"  # Update path as needed
# ocr_text = ocr_pdf_to_text(pdf_path)

# # Optional: Truncate for large files
# # ocr_text = ocr_text[:3000]

# # Step 2: Extract transactions using LLM
# transactions = extract_transactions(ocr_text)
# print("\nExtracted Transactions:\n")
# print(transactions)

# # Time tracking
# end_time = time.time()
# print(f"\nProcessing completed in {end_time - start_time:.2f} seconds.")



# model.py

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Path to the locally saved model directory
model_path = "mistral"  # You can use full path like r"C:\models\mistral"

# Caching model and tokenizer so they load only once
model = None
tokenizer = None

def load_model():
    """Lazily loads the model and tokenizer only once."""
    global model, tokenizer
    if model is None or tokenizer is None:
        print("Loading model... (This may take time on CPU)")
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float32  # Use float32 for CPU
        ).to("cpu")
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        print("Model loaded.")

def build_prompt(ocr_text):
    return f"""You are a helpful assistant. Your task is to extract only the lines that represent financial transactions from the OCR bank statement text. These include debits, credits, interest payments, loan disbursements, recoveries, etc.

Return only the transaction lines exactly as they appear, without explanation or extra formatting.

NOTE: EACH TRANSACTION LINE MUST START WITH A DATE IN THE FORMAT DD-MMM-YYYY (e.g., 09-Apr-2023). ALSO BEFORE THE DATE THERE CAN APPEAR SOME EXTRA SYMBOLS LIKE =, ;, :, =!

Here are some examples of a valid transaction line:

09-Apr-2023 2004204258873001 Loan Disbursement Debit 2,000,000.00 -2,000,000.00
; 09-Aug-2023 6042588730002 Penal Int 58.35 -1,810,963.63
= 09-May-2023 Loan Recovery From -2004204258873007 82,104.00 -1,332 896.00
: 08-Jun-2023 Loan Recovery From -2004204258873001 82,104.00 -1,865,288.72

An invalid transaction line would be:

RAHMAN ELECTRIC AND HARDWARE Cust ID 04258873

Now extract transaction lines from this text:

{ocr_text}

Transaction lines:"""

def extract_transactions(text):
    """Main callable function to extract transaction lines from OCR text using LLM."""
    load_model()  # Lazy loading model on demand
    prompt = build_prompt(text)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=1500,
            temperature=0.2,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id
        )

    decoded = tokenizer.decode(output[0], skip_special_tokens=True)

    if "Transaction lines:" in decoded:
        return decoded.split("Transaction lines:")[-1].strip()
    return decoded.strip()
