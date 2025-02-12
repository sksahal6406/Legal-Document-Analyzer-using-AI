from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import os
from django.core.files.storage import FileSystemStorage
import json

import pytesseract
from pdf2image import convert_from_path

# for Image Processing
import cv2
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

# for pdf to text
import pytesseract
from pdf2image import convert_from_path
import fitz
import easyocr
import torch

# for language translation and speech translation
from deep_translator import GoogleTranslator
from gtts import gTTS
import groq
import time


################################################ functions ################################################

def generate_speech(text, language):
    filename = 'voice.mp3'
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    translated_text = translate_text(text, language)
    tts = gTTS(text=translated_text, lang=language, slow=False)
    tts.save(file_path)

    return filename


def translate_text(text, language):
    time.sleep(3)
    translator = GoogleTranslator(source='auto', target=language)
    result = translator.translate(text)
    print(result)
    return result


# def extract_text(pdf_path):
#     images = convert_from_path(pdf_path)
#     text = "\n".join([pytesseract.image_to_string(image) for image in images])
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


import groq

def optimize_text_using_groq(text):
    # Initialize the Groq Client correctly
    client = groq.Client(api_key="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")

    # Make a request to the completions API
    response = client.chat.completions.create(
        model="llama3-8b-8192",  # Ensure this model is valid
        messages=[
            {"role": "system", "content": "you are an english expert assistant, profficient in english."},
            {"role": "user", "content": f'correct all the errors in this text and remove bold, italics and underlines styles from the characters,and in the result just provide me the resultant text dont include anything else also give the text in the same formate as the input text{text}'},
        ]
    )

    # Extract the optimized text from the response
    optimized_text = response.choices[0].message.content
    return optimized_text





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
        optimized_text = optimize_text_using_groq(extracted_text)
        print("optimized_text"+optimized_text)
        translated_text = translate_text(optimized_text, language)


        return render(request, 'analyze.html', {
            'extracted_text': optimized_text,
            'translated_text': translated_text,
        })

    return render(request, 'analyze.html')


def text_to_speech(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('text')
        language = data.get('language')
        print(text + "\n\n\n\n" + language)

        audio_path = generate_speech(text, language)
        

        # Construct file URL
        file_url = request.build_absolute_uri(settings.MEDIA_URL + audio_path)

        return JsonResponse({'success': True, 'voice_url': file_url})

    return JsonResponse({'success': False, 'message': 'Invalid request'})
 
def ask_prompt(request):
    client=groq.Client(api_key="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")
    data=json.loads(request.body)
    text=data.get('text')
    opt_text=data.get('opt_text')
    print("heello"+text)
    response=client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": f"You Are A Good Indian Lawyer, Well Educated about Indian Law. The Text Is {opt_text} Answer any questions regarding this "},
            {"role": "user", "content": text},
        ]
        
    )
    output=response.choices[0].message.content
    return JsonResponse({"Response":output})