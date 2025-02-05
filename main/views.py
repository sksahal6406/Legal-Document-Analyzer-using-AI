from django.shortcuts import render
import pytesseract
from pdf2image import convert_from_path

# Create your views here.


def extract_text(pdf_path):
    images=convert_from_path(pdf_path)
    text="\n".join([pytesseract.image_to_string(image) for image in images])
    return text

print(extract_text("Scanned Page.pdf"))