from pdf2image import convert_from_path
import pytesseract

# Set the Tesseract executable path (Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Set the Poppler binary path
POPPLER_PATH = r"C:\Users\mosta\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"

def ocr_pdf_to_text(pdf_path: str, lang: str = "eng") -> str:
    """
    Converts a PDF to images, performs OCR, and returns the full text.

    Args:
        pdf_path (str): Path to the input PDF file.
        lang (str): OCR language code (default is 'eng').

    Returns:
        str: Combined OCR text from all PDF pages.
    """
    images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)

    full_text = ""
    for i, img in enumerate(images):
        text = pytesseract.image_to_string(img, lang=lang)
        full_text += f"\n=== Page {i + 1} ===\n{text}\n"

    return full_text

# Example usage:
# text = ocr_pdf_to_text("Brac 1.pdf")
# print(text)
