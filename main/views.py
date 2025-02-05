from django.shortcuts import render
from django.http import HttpResponse,JsonResponse


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



################################################## views ###################################################

# Create your views here.
def index(request):
    return render(request, 'index.html')

def analyze(request):
    extract_text = "my name is sanket"
    translated_text = "hello world"
    translate_text(extract_text,'ta')

    return render(request, 'analyze.html', {'extracted_text':extract_text,'translated_text':translated_text})
    