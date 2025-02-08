from django.shortcuts import render
from django.http import HttpResponse,JsonResponse
from django.conf import settings
import os
from django.core.files.storage import FileSystemStorage
import json

import pytesseract
from pdf2image import convert_from_path

#for Image Proccessing
import cv2
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

# for pdf to text
import pytesseract
from pdf2image import convert_from_path
import fitz

# for language translation and speech translation
from googletrans import Translator
from gtts import gTTS

################################################ functions ################################################

def generate_speech(text, language):
    filename = 'voice.mp3'
    file_path = os.path.join(settings.MEDIA_ROOT, filename)

    tts = gTTS(text=text, lang=language, slow=False)
    tts.save(file_path)

    return filename



def translate_text(text,language):
    translator = Translator()
    result = translator.translate(text, dest=language)
    # generate_speech(result.text)
    print(result.text)
    return result.text

# def extract_text(pdf_path):
#     images=convert_from_path(pdf_path)
#     text="\n".join([pytesseract.image_to_string(image) for image in images])
#     return text

# print(extract_text("Scanned Page.pdf"))

def extract_text_from_pdf(pdf_filename):
    # Construct the full path to the PDF in media/uploads
    pdf_path = os.path.join(settings.BASE_DIR, 'media', 'uploads', pdf_filename)

    text = ""
    doc = fitz.open(pdf_path)  # Open the PDF
    for page in doc:
        text += page.get_text("text") + "\n"  # Extract text
    return text

################################################## views ###################################################

# Create your views here.
def index(request):
    return render(request, 'index.html')

def analyze(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        pdf_file = request.FILES['pdf_file']  # Get the uploaded file
        language = request.POST['language']   # Get the selected language

        # Define the folder where the PDF will be stored
        upload_folder = os.path.join(settings.MEDIA_ROOT, 'uploads')

        # Create the folder if it doesn’t exist
        os.makedirs(upload_folder, exist_ok=True)

        # Save the file inside the "uploads" folder
        fs = FileSystemStorage(location=upload_folder)
        filename = fs.save(pdf_file.name, pdf_file)

        # Get the full path of the saved file
        saved_file_url = fs.url(os.path.join('uploads', filename))

        # Extract text from the PDF
        extracted_text = extract_text_from_pdf(filename)
        translated_text = translate_text(extracted_text,language)

        return render(request, 'analyze.html',{
            'extracted_text': extracted_text,
            'translated_text': translated_text,
        })

    return render(request, 'analyze.html')
    
def text_to_speech(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('text')
        language = data.get('language')

        audio_path = generate_speech(text, language)

        # Construct file URL
        file_url = request.build_absolute_uri(settings.MEDIA_URL + audio_path)

        return JsonResponse({'success': True, 'voice_url': file_url})

    return JsonResponse({'success': False, 'message': 'Invalid request'})