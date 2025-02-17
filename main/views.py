from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import os
from django.core.files.storage import FileSystemStorage
import json
from PIL import Image
import fitz
from deep_translator import GoogleTranslator
from gtts import gTTS
from google import genai
from google.genai import types
from pdf2image import convert_from_path
import groq
import time
import speech_recognition as sr
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from pydub import AudioSegment

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


def extract_text_from_pdf(pdf_filename):
    pdf_path = os.path.join(settings.BASE_DIR, 'media', 'uploads', pdf_filename)
    text = ""
    doc = fitz.open(pdf_path)  # Open the PDF
    for page in doc:
        text += page.get_text("text") + "\n"  # Extract text
    return text


def optimize_text_using_groq(text):
    client = groq.Client(api_key="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")
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "you are an English expert assistant."},
            {"role": "user", "content": f'Correct errors and remove formatting from this text: {text}'},
        ]
    )
    return response.choices[0].message.content
    
    



def generate_summary(text):
    client = groq.Client(api_key="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")
    client = groq.Client(api_key="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")
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "user", "content": f"Summarize this text in plain words: {text}"},
        ]
    )
    return response.choices[0].message.content

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
        extracted_text = extract_text_from_pdf(filename)
        optimized_text = optimize_text_using_groq(extracted_text)
        translated_text = translate_text(optimized_text, language)
        summary_text = generate_summary(optimized_text)
        translated_summary = translate_text(summary_text, language)
        return render(request, 'analyze.html', {
            'extracted_text': optimized_text,
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
        # client = groq.Client(api_key="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")
        client=genai.Client(api_key="AIzaSyBu2ilS5D1MG84uTVZCKNCzntqjk3Pym0w")
        data = json.loads(request.body)
        ptype = data.get("type")
        opt_text = data.get('opt_text')
        text = ""
        if ptype == "Legality":
            text = "Check the legality of the text and list ambiguities in HTML list tags. If none, return 'None'."
        elif ptype == "Sections":
            text = "List out all the relevant sections and laws in HTML list tags. If none, return 'None'."
        elif ptype == "Errors":
            text = "Check for grammatical errors and list them in HTML list tags. If none, return 'None'."
        elif ptype=="Mannual":
            text=data.get('text')
        # response = client.chat.completions.create(
        #     model="llama3-8b-8192",
        #     messages=[
        #         {"role": "system", "content": f"You are an expert in Indian law. The text is {opt_text}."},
        #         {"role": "user", "content": text},
        #     ]
        # )
        sys_msg=f'''You are an expert Indian lawyer, highly knowledgeable in the Indian Constitution, legal statutes, case laws, and judicial practices.Analyse This Data {opt_text} You provide accurate, well-reasoned, and precise legal responses based on the principles of Indian law. Your responses reflect a deep understanding of constitutional provisions, statutory interpretations, procedural laws, and judicial precedents.

When answering questions, you ensure clarity, correctness, and legal accuracy, referencing relevant laws, acts, and landmark judgments when applicable. If legal ambiguities exist, you explain differing interpretations and judicial opinions.

Maintain a formal, professional, and objective tone while avoiding personal opinions. If a query requires legal advice, you clarify that you are providing information and not personalized legal representation.

If a question falls outside Indian law, explicitly state the limitation and, if relevant, provide general comparative legal insights. Avoid making up laws or offering speculative legal interpretations. Answer Everything Precisely and without any uneccessary text except the answer'''

        response=client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(system_instruction=sys_msg),
            contents=[{"text":text}]
        )
        
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
