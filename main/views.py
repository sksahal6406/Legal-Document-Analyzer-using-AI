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

import speech_recognition as sr
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


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
    if request.method=="POST":
        
        client=groq.Client(api_key="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")
        data=json.loads(request.body)
        ptype=data.get("type")
        opt_text=data.get('opt_text')
        print(ptype)
        if(ptype=="Mannual"):
            text=data.get('text')
            print("heello"+text)
            
        elif(ptype=="Legality"):
            text="Check For The Legality Of The Text and Also Provide the Possible Ambiguities. Give the points in html list tags. If It Doesnt Then Just Gives the output as None and nothing else "
            
        elif(ptype=="Sections"):
            
            text="List Out All The Sections and Laws this text pertains to. List Out The Sections in HTML LIST Tags. If It Does Not then simple give the output as None and nothing else"
            
        elif(ptype=="Errors"):
            text="Check The Text For Any Grammatical Errors In the text and list them in HTML List Tags and if there are none then just give the output as none "    
            
        response=client.chat.completions.create(
            model="llama3-8b-8192",

            messages=[
                {"role": "system", "content": f"You Are A Good Indian Lawyer, Well Educated about Indian Law. The Text Is {opt_text} Answer any questions regarding this. In The Output There Should be no Unecesarry Text From You Except What is asked"},
                {"role": "user", "content": text},
            ]

        )
        output=response.choices[0].message.content
        return JsonResponse({"Response":output})


import speech_recognition as sr
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from pydub import AudioSegment
import os

def audio_to_text(request):
    if request.method == 'POST' and request.FILES.get('audio_file'):
        try:
            # Get the uploaded file
            audio_file = request.FILES['audio_file']
            original_file_path = f'media/{audio_file.name}'
            print(audio_file)
            print(original_file_path)
            path = default_storage.save(original_file_path, ContentFile(audio_file.read()))

            # Convert to PCM WAV format with 16-bit sample width and 16kHz sample rate
            # new_original_file_path = f'media/{original_file_path}'
            converted_file_path = original_file_path.replace('.wav', '_converted.wav')
            print(converted_file_path)
            audio = AudioSegment.from_file(f'media/{original_file_path}')
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            audio.export(f'media/{converted_file_path}', format="wav")

            # Perform speech recognition
            recognizer = sr.Recognizer()
            with sr.AudioFile(f'media/{converted_file_path}') as source:
                print("Recognizing...")
                print(converted_file_path)
                audio_data = recognizer.record(source)
                transcription = recognizer.recognize_google(audio_data)
                

            # Clean up temporary files
            os.remove(f'media/{original_file_path}')
            os.remove(f'media/{converted_file_path}')

            return JsonResponse({'transcription': transcription})

        except sr.UnknownValueError:
            return JsonResponse({'error': 'Speech recognition failed: Could not understand the audio'})
        except sr.RequestError as e:
            return JsonResponse({'error': f'Error occurred during speech recognition: {e}'})
        except Exception as e:
            return JsonResponse({'error': f'An error occurred: {str(e)}'})

    return JsonResponse({'error': 'Invalid request'}, status=400)




        