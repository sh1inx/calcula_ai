from fastapi import FastAPI
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from gradio_client import Client
import re

tradutor = GoogleTranslator(source="en", target="pt")
app = FastAPI()

class InputModel(BaseModel):
    valor: str

def extrair_resposta(texto):
    match = re.search(r"(\d+(\.\d+)?)", texto)
    if match:
        return match.group(1).strip()
    return "Resposta não encontrada."

@app.post("/processar")
async def processar_expressao(input_data: InputModel):
    client = Client("eribur/Basic_math_agent")
    result = client.predict(
        message=input_data.valor,
        api_name="/chat"
    )
    
    traducao = tradutor.translate(result)
    resposta_somente = extrair_resposta(traducao)
    
    return {"valor": resposta_somente}