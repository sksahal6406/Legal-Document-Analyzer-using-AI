from django.shortcuts import render
from django.http import HttpResponse,JsonResponse
from django.conf import settings
import os
from django.core.files.storage import FileSystemStorage


# for pdf to text
import pytesseract
from pdf2image import convert_from_path

# for language translation and speech translation
from googletrans import Translator
from gtts import gTTS

################################################ functions ################################################

def text_to_speech(text):
    tts = gTTS(text=text, lang='ta',slow=False)
    tts.save(f'{text}.mp3')



def translate_text(text,language):
    translator = Translator()
    result = translator.translate(text, dest=language)
    text_to_speech(result.text)
    print(result.text)
    return result.text

# def extract_text(pdf_path):
#     images=convert_from_path(pdf_path)
#     text="\n".join([pytesseract.image_to_string(image) for image in images])
#     return text

# print(extract_text("Scanned Page.pdf"))



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

        print("Saved PDF Path:", saved_file_url)
        print("Selected Language:", language)

        return render(request, 'analyze.html', {'pdf_path': saved_file_url, 'language': language})

    return render(request, 'analyze.html')
    
