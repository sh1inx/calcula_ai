from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from deep_translator import GoogleTranslator
from gradio_client import Client
import re

tradutor = GoogleTranslator(source="en", target="pt")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InputModel(BaseModel):
    tipo: str
    texto: str

def extrair_resposta(texto):
    match = re.search(r"(\d+(\.\d+)?)", texto)
    if match:
        return match.group(1).strip()
    return "Resposta não encontrada."

operacao_pendente = None

@app.post("/processar")
async def processar_expressao(input_data: InputModel):
    global operacao_pendente
    try:
        if input_data.tipo == "pergunta":
            texto = input_data.texto.lower()
            if "somar" in texto or "soma" in texto:
                operacao_pendente = "soma"
                return {"resposta": "Por favor, informe os números que deseja somar, separados por vírgula."}
            elif "multiplicar" in texto or "multiplicação" in texto:
                operacao_pendente = "multiplicacao"
                return {"resposta": "Por favor, informe os números que deseja multiplicar, separados por vírgula."}
            else:
                operacao_pendente = None
                client = Client("eribur/Basic_math_agent")
                result = client.predict(
                    message=input_data.texto,
                    api_name="/chat"
                )
                traducao = tradutor.translate(result)
                resposta_somente = extrair_resposta(traducao)
                return {"resposta": f"Resultado: {resposta_somente}"}

        elif input_data.tipo == "valores":
            if not operacao_pendente:
                return {"resposta": "Nenhuma operação pendente. Por favor, faça uma pergunta primeiro."}
            try:
                numeros = [float(x.strip()) for x in input_data.texto.split(",")]
            except Exception:
                return {"resposta": "Erro: valores inválidos. Envie números separados por vírgula."}
            
            if operacao_pendente == "soma":
                resultado = sum(numeros)
            elif operacao_pendente == "multiplicacao":
                resultado = 1
                for n in numeros:
                    resultado *= n
            else:
                resultado = None
            
            operacao_pendente = None
            if resultado is None:
                return {"resposta": "Operação desconhecida."}
            return {"resposta": f"O resultado da {operacao_pendente or 'operação'} é {resultado}"}

        else:
            return {"erro": "Tipo inválido. Use 'pergunta' ou 'valores'."}

    except Exception as e:
        print(f"Erro ao processar a expressão: {str(e)}")
        return {"erro": "Erro ao processar a expressão."}
