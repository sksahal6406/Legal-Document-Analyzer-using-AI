from django.shortcuts import render
from django.http import HttpResponse,JsonResponse

import pytesseract
from pdf2image import convert_from_path

#for Image Proccessing
import cv2
import numpy as np
from PIL import Image
import easyocr
import torch

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


def extract_text(pdf_path):
    
    images=convert_from_path(pdf_path)
    for i,img in enumerate(images):
        img_path=f"E:\DJango Projects\LegalAI\images\img_{i+1}.png"
        img.save(img_path,"PNG")
    #     print(f"Extracted: {img_path}")
    # # for image in images:
    #     dpi = img.info.get("dpi")
    #     img=cv2.imread(img_path,dpi)
    #     gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    #     # cv2.imwrite(f"test_{i+1}.png",gray)
    #     contrast=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8))
    #     contrast_img=contrast.apply(gray)
        
    #     blurred=cv2.GaussianBlur(contrast_img,(5,5),0)

    #     _,binary=cv2.threshold(blurred,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        reader=easyocr.Reader(['mr'])
        # cv2.imwrite(img,binary)
        texts=reader.readtext(img_path,detail=0)
        for text in texts:
            print(text)
    #     text="\n".join([pytesseract.image_to_string(binary,config="--psm 6 --oem 3")])
    #     print(text)
    


print(extract_text("E:\DJango Projects\LegalAI\\rent.pdf"))

################################################## views ###################################################

# Create your views here.
def index(request):
    return render(request, 'index.html')

def analyze(request):
    extract_text = "my name is sanket"
    translated_text = "hello world"
    translate_text(extract_text,'ta')
 
    return render(request, 'analyze.html', {'extracted_text':extract_text,'translated_text':translated_text})
    
