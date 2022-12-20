import json
from django.http import JsonResponse
from django.http import HttpResponse
# Create your views here.
import torch

from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import permissions

from transformers import AutoTokenizer,T5ForConditionalGeneration
import re
from django.views.decorators.csrf import csrf_exempt
from scipy.spatial.distance import cosine

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

model = T5ForConditionalGeneration.from_pretrained("./models-20")
tokenizer = AutoTokenizer.from_pretrained('t5-small')

@csrf_exempt
def questionGeneration(request):
    if request.method =='GET':
        return HttpResponse("Reponse for GET request from /question-grading")

    if request.method =='POST':
        print(request)
        data = json.loads(request.body)
        sentence = data['sentence']
        sentence=tokenizer(sentence,return_tensors="pt")
        outs = model.generate(input_ids=sentence['input_ids'], attention_mask=sentence['attention_mask'],max_length=512,early_stopping=True,num_beams=5,num_return_sequences=5)
        outs=[tokenizer.decode(ids) for ids in outs]
        questions=[]
        for s in outs:
            s=re.sub(r'<pad>', '', s)
            s=re.sub(r'</s>', '', s)
            questions.append(s)
        return JsonResponse({"questions":questions})

@csrf_exempt
def questionGrading(request):
    if request.method =='GET':
        return HttpResponse("Reponse for GET request from /question-generation")

    if request.method =='POST':
        data = json.loads(request.body)

        sentence1 = data['sentence1']
        sentence2 = data['sentence2']

        tokens1 = tokenizer(sentence1, return_tensors="pt",max_length=10,pad_to_max_length=True)
        tokens2 = tokenizer(sentence2, return_tensors="pt",max_length=10,pad_to_max_length=True)

        output1 = model.encoder(
            input_ids=tokens1["input_ids"],
            attention_mask=tokens1["attention_mask"],
            return_dict=True,
        )

        output2 = model.encoder(
            input_ids=tokens2["input_ids"], 
            attention_mask=tokens2["attention_mask"], 
            return_dict=True,
        )

        # output1=output1.last_hidden_state.detach()
        # output2=output2.last_hidden_state.detach()

        # output1=output1.numpy()
        # output2=output2.numpy()

        # output1 = output1.reshape(-1)
        # output2 = output2.reshape(-1)

        # o1=output1.last_hidden_state
        # o2=output2.last_hidden_state

        o1=output1
        o2=output2

        # o1 = torch.mean(o1, dim=1)
        # o2 = torch.mean(o2, dim=1)
        o1=(o1.last_hidden_state * tokens1["attention_mask"].unsqueeze(-1)).sum(dim=-2) / tokens1["attention_mask"].sum(dim=-1)
        o2=(o2.last_hidden_state * tokens2["attention_mask"].unsqueeze(-1)).sum(dim=-2) / tokens2["attention_mask"].sum(dim=-1)

        o1=o1.detach().numpy()
        o2=o2.detach().numpy()

        o1 = o1.reshape(-1)
        o2 = o2.reshape(-1)

        similarity=1-cosine(o1,o2)
        return JsonResponse({"grade":similarity})