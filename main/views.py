from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import os
from django.core.files.storage import FileSystemStorage
import json
from PIL import Image
import fitz
from deep_translator import GoogleTranslator, exceptions
from gtts import gTTS
import google.generativeai as genai
# from google import genai as cgenai
# from google.genai import types
# from google.generativeai import types
from io import BytesIO
import speech_recognition as sr
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from pydub import AudioSegment
import time
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import io
import base64



################################################ functions ################################################

# client = cgenai.Client(api_key="AIzaSyBu2ilS5D1MG84uTVZCKNCzntqjk3Pym0w")
genai.configure(api_key="AIzaSyBu2ilS5D1MG84uTVZCKNCzntqjk3Pym0w")
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction="you are an expert in extracting text from pdfs"
)


# def extract_text_from_written_pdf(pdf_path):
#     pdf_document = fitz.open(pdf_path)
#     text = ""
#     for page_number in range(len(pdf_document)):
#         page = pdf_document[page_number]
#         text += page.get_text()
#     return text
# def extract_text_from_written_pdf(pdf_path):
#     pdf_document = fitz.open(pdf_path)
#     with ThreadPoolExecutor() as executor:
#         text_list = list(executor.map(lambda page: page.get_text("text"), pdf_document))

#     # os.remove(pdf_path)
#     return "".join(text_list)

import fitz  # PyMuPDF
import io
import base64
import concurrent.futures
from PIL import Image
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key="AIzaSyBu2ilS5D1MG84uTVZCKNCzntqjk3Pym0w")  # Replace with your API Key
model = genai.GenerativeModel("gemini-pro-vision")


import fitz
import concurrent.futures
import base64
import io
import os

def process_page(pdf_path, page_number):
    """Processes a single page: converts it to an image and prepares it for Gemini."""
    try:
        if not os.path.exists(pdf_path):
            return None  # Handle inaccessible files gracefully
        
        pdf_document = fitz.open(pdf_path)  # Open inside the function to avoid cross-process issues
        page = pdf_document[page_number]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # Lower resolution for speed
        img_bytes = pix.tobytes("png")  # Direct conversion to PNG bytes

        # Encode to Base64
        encoded_image = base64.b64encode(img_bytes).decode("utf-8")

        return {"mime_type": "image/png", "data": encoded_image}
    except Exception as e:
        print(f"Error processing page {page_number}: {e}")
        return None

def process_page_text(image, model):
    """Extracts text from an image using Gemini Pro Vision."""
    try:
        response = model.generate_content([
            "Extract text from this PDF page and ignore any QR codes or pictures. Display it neatly.",
            image,
        ])
        return response.text if response.text else "No text extracted."
    except Exception as e:
        print(f"Error extracting text: {e}")
        return "Error extracting text."

def extract_text_from_written_pdf(pdf_path, model):
    """Extracts text from a scanned PDF using Gemini Pro Vision with optimized processing."""
    try:
        if not os.path.exists(pdf_path):
            return "Error: PDF file is inaccessible."

        pdf_document = fitz.open(pdf_path)
        num_pages = len(pdf_document)

        # Use ProcessPoolExecutor for CPU-intensive image processing
        with concurrent.futures.ProcessPoolExecutor() as executor:
            images = list(executor.map(process_page, [pdf_path] * num_pages, range(num_pages)))

        # Remove failed pages
        images = [img for img in images if img is not None]
        if not images:
            return "Error: No pages were successfully processed."

        # Use ThreadPoolExecutor for API calls (I/O-bound)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(process_page_text, images, [model] * len(images)))

        return "\n\n".join(results)

    except Exception as e:
        print(f"Error processing PDF: {e}")
        return "Error processing PDF."


# Example Usage





# def extract_text_from_written_pdf(pdf_path):
#     """Extracts text from a PDF by converting pages to images and using Gemini Pro Vision."""
    
#     pdf_document = fitz.open(pdf_path)
#     extracted_text = []

#     # Gemini Model
#     model = genai.GenerativeModel("gemini-pro-vision")

#     for page_num in range(len(pdf_document)):
#         page = pdf_document[page_num]

#         # Convert PDF page to an image
#         pix = page.get_pixmap()
#         img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

#         # Convert image to bytes (for Gemini input)
#         img_byte_arr = io.BytesIO()
#         img.save(img_byte_arr, format="PNG")
#         img_byte_arr = img_byte_arr.getvalue()

#         # Send image to Gemini for text extraction
#         response = model.generate_content(
#             [
#                 "Extract text from the PDF and ignore any QR codes or pictures.",
#                 img_byte_arr
#             ]
#         )

#         # Store extracted text
#         if response and hasattr(response, "text"):
#             extracted_text.append(response.text)

#     return "\n".join(extracted_text)

def generate_speech(text, language):
    filename = 'voice.mp3'
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    translated_text = translate_text(text, language)
    tts = gTTS(text=translated_text, lang=language, slow=False)
    tts.save(file_path)
    return filename

# def translate_text(text, language):
#     time.sleep(3)
#     max_chars = 4500
#     chunks = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
#     translate_texts = []
#     for chunk in chunks:
#         translator = GoogleTranslator(source='auto', target=language)
#         translate_texts.append(translator.translate(chunk))
#     translated_text = ' '.join(translate_texts)
#     return translated_text


def translate_chunk(chunk_language):
    """Translate a given text chunk to the target language."""
    chunk, language = chunk_language  # Unpack tuple
    time.sleep(1)  # Prevent rate limits
    try:
        translator = GoogleTranslator(source='auto', target=language)
        return translator.translate(chunk)
    except exceptions.RequestError as e:
        print(f"Request error: {e}")
        return "[Translation Error]"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "[Translation Error]"

def translate_text(text, language):
    """Split text into chunks and translate in parallel."""
    max_chars = 2000
    chunks = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
    
    with concurrent.futures.ProcessPoolExecutor() as executor:
        translated_chunks = list(executor.map(translate_chunk, [(chunk, language) for chunk in chunks]))

    return ' '.join(translated_chunks)

# def extract_images_from_pdf(pdf_path):
#     images = []
#     with fitz.open(pdf_path) as pdf_document:
#         images = [
#             Image.open(BytesIO(pdf_document.extract_image(img[0])["image"]))
#             for page in pdf_document
#             for img in page.get_images(full=True)
#         ]
#     return images

# def extract_text_from_image(image):
#     model = genai.GenerativeModel("gemini-2.0-flash")
#     prompt = "Extract text from this and ignore any qr codes or other elements"
#     response = model.generate_content([prompt, image])
#     return response.text if response.text else ""

# def extract_text_from_pdf(pdf_path):
#     images = extract_images_from_pdf(pdf_path)
    
#     # If no images, process as a written PDF
#     if not images:
#         return extract_text_from_written_pdf(pdf_path,model=model)  # Assuming this function is defined elsewhere

#     # Process images concurrently
#     extracted_texts = []
#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         results = executor.map(extract_text_from_image, images)
#         extracted_texts.extend(results)
    
#     return "\n".join(extracted_texts)

def optimize_text_using_groq(text):
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f'While preserving the original line breaks and paragraph structure maintain the existing layout and Return only the extracted text as it is in the PDF: {text}'
    response = model.generate_content([prompt, text])
    return response.text

# def generate_summary(text):
#     model = genai.GenerativeModel("gemini-2.0-flash")
#     prompt = "Summarize this text in words understandable by a layman,do not add anything extra But Do not miss out on any points."
#     response = model.generate_content([prompt, text])
#     return response.text
model = genai.GenerativeModel("gemini-2.0-flash")
def summarize_chunk(chunk):
    prompt = "Summarize this text in words understandable by a layman. Do not add anything extra, but do not miss out on any points."
    response = model.generate_content([prompt, chunk])
    return response.text

def generate_summary(text, max_chars=3000):
    chunks = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor() as executor:
        summaries = list(executor.map(summarize_chunk, chunks))

    return ' '.join(summaries)

def summarize_large_text(text, chunk_size=2000):
    # model = genai.GenerativeModel('gemini-pro')

    # Split text into chunks
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    # Function to process each chunk in parallel
    def summarize_chunk(chunk):
        prompt = f"Summarize the following text concisely:\n\n{chunk}"
        response = model.generate_content(prompt, stream=True)
        return "".join(chunk.text for chunk in response)  # Streaming response

    # Use ThreadPoolExecutor to process chunks in parallel
    with ThreadPoolExecutor() as executor:
        summaries = list(executor.map(summarize_chunk, chunks))

    # Merge all summaries
    final_prompt = "Combine these summaries into a single concise summary:\n\n" + '\n'.join(summaries)
    final_summary = model.generate_content(final_prompt, stream=True)

    return "".join(chunk.text for chunk in final_summary)

################################################## views ###################################################

def index(request):
    return render(request, 'index.html')

def analyze(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        pdf_file = request.FILES['pdf_file']
        language = request.POST['language']
        upload_folder = os.path.join(settings.MEDIA_ROOT, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        fs = FileSystemStorage(location=upload_folder)
        filename = fs.save(pdf_file.name, pdf_file)
        extracted_text = extract_text_from_written_pdf(os.path.join("media", "uploads", filename),model=model)
        print(extracted_text)
        # optimized_text = optimize_text_using_groq(extracted_text)
        translated_text = translate_text(extracted_text, language)
        print(translate_text)
        summary_text = summarize_large_text(extracted_text)
        print(summary_text)
        translated_summary = translate_text(summary_text, language)
        return render(request, 'analyze.html', {
            'extracted_text': extracted_text,
            'translated_text': translated_text,
            'summary_text': translated_summary
        })
    return render(request, 'analyze.html')

def text_to_speech(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('text')
        language = data.get('language')
        audio_path = generate_speech(text, language)
        file_url = request.build_absolute_uri(settings.MEDIA_URL + audio_path)
        return JsonResponse({'success': True, 'voice_url': file_url})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def ask_prompt(request):
    if request.method == "POST":
        data = json.loads(request.body)
        ptype = data.get("type")
        opt_text = data.get('opt_text')
        text = ""
        if ptype == "Legality":
            text = "Check the legality of the text and list ambiguities in a plain text with breaks and paragraph spacings. If none, return 'None'."
        elif ptype == "Sections":
            text = "List out all the relevant sections and laws.Provide it in a plain text with breaks and paragraph spacings. If none, return 'None'."
        elif ptype == "Errors":
            text = "Check for grammatical errors and provide it in a plain text with breaks and paragraph spacings. If none, return 'None'."
        elif ptype == "Mannual":
            text = data.get('text')
        sys_msg = f'''You are an expert Indian lawyer, highly knowledgeable in the Indian Constitution, legal statutes, case laws, and judicial practices.Analyse This Data {opt_text} You provide accurate, well-reasoned, and precise legal responses based on the principles of Indian law. Your responses reflect a deep understanding of constitutional provisions, statutory interpretations, procedural laws, and judicial precedents. When answering questions, you ensure clarity, correctness, and legal accuracy, referencing relevant laws, acts, and landmark judgments when applicable and explain simply. If legal ambiguities exist, you explain differing interpretations and judicial opinions. Maintain a formal, professional, and objective tone while avoiding personal opinions. If a query requires legal advice, you clarify that you are providing information and not personalized legal representation. If a question falls outside Indian law, explicitly state the limitation and, if relevant, provide general comparative legal insights. Avoid making up laws or offering speculative legal interpretations. Answer Everything Precisely and without any uneccessary text except the answer. Provide the answer only in a proper format.'''
        # response = client.models.generate_content(
        #     model="gemini-2.0-flash",
        #     config=types.GenerateContentConfig(system_instruction=sys_msg),
        #     contents=[{"text": text}]
        # )
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=sys_msg
        )
        response = model.generate_content(
            contents=[{"text": text}]
        )
        print(response.text)
        return JsonResponse({"Response": response.text})

def audio_to_text(request):
    if request.method == 'POST' and request.FILES.get('audio_file'):
        try:
            audio_file = request.FILES['audio_file']
            original_file_path = f'media/{audio_file.name}'
            path = default_storage.save(original_file_path, ContentFile(audio_file.read()))
            converted_file_path = original_file_path.replace('.wav', '_converted.wav')
            audio = AudioSegment.from_file(f'media/{original_file_path}')
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            audio.export(f'media/{converted_file_path}', format="wav")
            recognizer = sr.Recognizer()
            with sr.AudioFile(f'media/{converted_file_path}') as source:
                audio_data = recognizer.record(source)
                transcription = recognizer.recognize_google(audio_data)
            os.remove(f'media/{original_file_path}')
            os.remove(f'media/{converted_file_path}')
            return JsonResponse({'transcription': transcription})
        except sr.UnknownValueError:
            return JsonResponse({'error': 'Could not understand the audio'})
        except sr.RequestError as e:
            return JsonResponse({'error': f'Error during speech recognition: {e}'})
        except Exception as e:
            return JsonResponse({'error': f'An error occurred: {str(e)}'})
    return JsonResponse({'error': 'Invalid request'}, status=400)