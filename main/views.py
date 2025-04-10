from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import os
from django.core.files.storage import FileSystemStorage
import json
from gtts import gTTS
import google.generativeai as genai
from io import BytesIO
import speech_recognition as sr
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from pydub import AudioSegment
import time
import concurrent.futures
import fitz
from deep_translator import GoogleTranslator, exceptions
import base64

################################################ functions ################################################

genai.configure(api_key="AIzaSyBu2ilS5D1MG84uTVZCKNCzntqjk3Pym0w")
gemini_pro_vision = genai.GenerativeModel("gemini-1.5-flash")
gemini_flash = genai.GenerativeModel("gemini-2.0-flash")


def process_pdf_page(pdf_path, page_number):
    """Processes a single PDF page: converts to image (if needed) and prepares for Gemini."""
    try:
        with fitz.open(pdf_path) as pdf_document:
            page = pdf_document[page_number]
            is_pure_text = page.get_text() != "" and not page.get_images()
            if is_pure_text:
                return {"text": page.get_text("text")}
            else:
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_bytes = pix.tobytes("png")
                encoded_image = base64.b64encode(img_bytes).decode("utf-8")
                return {"image": {"mime_type": "image/png", "data": encoded_image}}
    except Exception as e:
        print(f"Error processing page {page_number}: {e}")
        return None

def extract_text_from_pdf_page(page_data):
    """Extracts text from a single PDF page's data using Gemini."""
    try:
        if "text" in page_data:
            return page_data["text"]
        elif "image" in page_data:
            response = gemini_pro_vision.generate_content([
                "Extract text from this PDF page and ignore any QR codes or pictures. Display it neatly.",
                page_data["image"],
            ])
            return response.text if response.text else ""
        return ""
    except Exception as e:
        print(f"Error extracting text from page: {e}")
        return ""

def extract_text_from_pdf_concurrent(pdf_path):
    """Extracts text from all pages of a PDF concurrently using Gemini, maintaining page order."""
    start_time = time.time()
    try:
        with fitz.open(pdf_path) as pdf_document:
            num_pages = len(pdf_document)
            page_data = [None] * num_pages  # Initialize a list to store page data in order
            extracted_texts = [None] * num_pages # Initialize a list to store extracted text in order

            with concurrent.futures.ProcessPoolExecutor() as executor:
                futures = {executor.submit(process_pdf_page, pdf_path, i): i for i in range(num_pages)}
                for future in concurrent.futures.as_completed(futures):
                    index = futures[future]
                    page_data[index] = future.result()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(extract_text_from_pdf_page, page_data[i]): i for i in range(num_pages)}
                for future in concurrent.futures.as_completed(futures):
                    index = futures[future]
                    extracted_texts[index] = future.result()

            extraction_time = time.time() - start_time
            print(f"Extraction time: {extraction_time} seconds")
            return "\n\n".join(extracted_texts), extraction_time
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return "", 0

def generate_speech(text, language):
    filename = 'voice.mp3'
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    translated_text, _ = translate_text(text, language)
    print(f"File path in generate_speech: {file_path}")
    print(f"Type of translated_text: {type(translated_text)}")
    tts = gTTS(text=translated_text, lang=language, slow=False)
    print(f"Type of argument to tts.save(): {type(file_path)}")
    tts.save(file_path)
    return filename


def translate_chunk(chunk_language):
    """Translate a given text chunk to the target language."""
    chunk, language = chunk_language
    time.sleep(1)
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
    start_time = time.time()
    max_chars = 3000
    chunks = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

    with concurrent.futures.ProcessPoolExecutor() as executor:
        translated_chunks = list(executor.map(translate_chunk, [(chunk, language) for chunk in chunks]))

    translation_time = time.time() - start_time
    print(f"Translation time: {translation_time} seconds")
    return ' '.join(translated_chunks), translation_time

def summarize_chunk(chunk):
    prompt = "Summarize this text in words understandable by a layman. Do not add anything extra, but do not miss out on any points."
    response = gemini_flash.generate_content([prompt, chunk])
    return response.text

def generate_summary(text, max_chars=3000):
    start_time = time.time()
    chunks = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        summaries = list(executor.map(summarize_chunk, chunks))

    # Combine all chunk summaries into a single text
    combined_summary_text = " ".join(summaries)

    # Generate a final concise summary of the combined text
    final_summary_prompt = "Summarize the following text concisely in about 150 words: " + combined_summary_text
    final_summary_response = gemini_flash.generate_content([final_summary_prompt])
    final_summary = final_summary_response.text if final_summary_response.text else ""

    summary_time = time.time() - start_time
    print(f"Summary time: {summary_time} seconds")
    return final_summary, summary_time

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
        pdf_path = os.path.join("media", "uploads", filename)

        extracted_text, extraction_time = extract_text_from_pdf_concurrent(pdf_path)
        translated_text, translation_time = translate_text(extracted_text, language)
        summary_text, summary_time = generate_summary(extracted_text)
        translated_summary, _ = translate_text(summary_text, language) # No need to time the second translation

        return render(request, 'analyze.html', {
            'extracted_text': extracted_text,
            'translated_text': translated_text,
            'summary_text': translated_summary,
            'extraction_time': f"{extraction_time:.2f} seconds",
            'translation_time': f"{translation_time:.2f} seconds",
            'summary_time': f"{summary_time:.2f} seconds",
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
        prompt_text = ""
        if ptype == "Legality":
            prompt_text = "Check the legality of the text and list ambiguities in a plain text with breaks and paragraph spacings. If none, return 'None'."
        elif ptype == "Sections":
            prompt_text = "List out all the relevant sections and laws. Provide it in a plain text with breaks and paragraph spacings. If none, return 'None'."
        elif ptype == "Errors":
            prompt_text = "Check for grammatical errors and provide it in a plain text with breaks and paragraph spacings. If none, return 'None'."
        elif ptype == "Mannual":
            prompt_text = data.get('text')

        system_instruction = f'''You are an expert Indian lawyer, highly knowledgeable in the Indian Constitution, legal statutes, case laws, and judicial practices. Analyse This Data: {opt_text} You provide accurate, well-reasoned, and precise legal responses based on the principles of Indian law. Your responses reflect a deep understanding of constitutional provisions, statutory interpretations, procedural laws, and judicial precedents. When answering questions, you ensure clarity, correctness, and legal accuracy, referencing relevant laws, acts, and landmark judgments when applicable and explain simply. If legal ambiguities exist, you explain differing interpretations and judicial opinions. Maintain a formal, professional, and objective tone while avoiding personal opinions. If a query requires legal advice, you clarify that you are providing information and not personalized legal representation. If a question falls outside Indian law, explicitly state the limitation and, if relevant, provide general comparative legal insights. Avoid making up laws or offering speculative legal interpretations. Answer Everything Precisely and without any unnecessary text except the answer. Provide the answer only in a proper format. **Do not use any markdown formatting like bold text, headings, lists with special characters, etc. Return only the plain text.**\n\n'''

        final_prompt = system_instruction + prompt_text

        response = gemini_flash.generate_content([{"text": final_prompt}])
        return JsonResponse({"Response": response.text})
    return JsonResponse({"error": "Invalid request method."}, status=400)


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