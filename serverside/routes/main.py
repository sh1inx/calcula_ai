from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import random
import os
from datetime import datetime

class AlunoInput(BaseModel):
    acao: str
    operacao: str = None
    faixa_etaria: str = None
    resposta_aluno: str = None
    feedback_entendeu: bool = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

estado_sessao = {
    "id_sessao": None,
    "operacao_atual": None,
    "faixa_etaria_atual": None,
    "pergunta_atual_texto": None,
    "pergunta_atual_numeros": [],
    "resposta_correta_pergunta": None,
    "ultimo_exemplo_fornecido": None,
    "tentativas_exemplo_atual": 0,
    "log_interacao_atual": {}
}

CSV_FILE = "aprendizado_log.csv"
CSV_HEADERS = [
    "timestamp", "id_sessao", "faixa_etaria", "operacao_solicitada",
    "pergunta_gerada", "numeros_pergunta", "resposta_aluno", "resposta_correta", "acertou_pergunta",
    "exemplo_fornecido_1", "entendeu_exemplo_1",
    "exemplo_fornecido_2", "entendeu_exemplo_2",
]

OBJETOS_POR_FAIXA = {
    "3-5": ["maçã", "bola", "gatinho", "carrinho", "doce"],
    "6-8": ["lápis", "figurinha", "moeda", "livro", "bala"],
    "9-12": ["jogo", "dinheiro", "página", "adesivo", "minuto"],
    "padrao": ["item", "unidade", "ponto"]
}
OPERACOES_SUPORTADAS = ["soma", "subtracao", "multiplicacao", "divisao"]
MAX_TENTATIVAS_EXEMPLO = 2

def obter_objeto_aleatorio(faixa_etaria: str) -> str:
    objetos = OBJETOS_POR_FAIXA.get(faixa_etaria, OBJETOS_POR_FAIXA["padrao"])
    return random.choice(objetos)

def pluralizar(palavra: str, quantidade: int) -> str:
    if quantidade == 1:
        return palavra
    if palavra.endswith('ão'):
        return palavra[:-2] + 'ões'
    elif palavra.endswith('m'):
        return palavra[:-1] + 'ns'
    elif palavra.endswith(('r', 's', 'z')):
        return palavra + 'es'
    elif palavra.endswith(tuple('aeiouln')):
         return palavra + "s"
    else:
        return palavra + 's'

def gerar_numeros_pergunta(operacao: str, faixa_etaria: str) -> tuple[int, int]:
    n1, n2 = 0, 0
    range_max = 5
    if faixa_etaria == "6-8": range_max = 10
    elif faixa_etaria == "9-12": range_max = 20

    n1 = random.randint(1, range_max)
    n2 = random.randint(1, range_max)

    if operacao in ["multiplicacao", "divisao"] and faixa_etaria != "3-5":
        n1 = random.randint(1, 10 if faixa_etaria != "9-12" else 12)
        n2 = random.randint(1, 5 if faixa_etaria != "9-12" else 10)
    
    if operacao == "subtracao":
        if n1 < n2: n1, n2 = n2, n1
        if n1 == n2 : n1 += random.randint(1,3)
            
    if operacao == "divisao":
        if n2 == 0: n2 = 1
        n1 = n2 * random.randint(1, range_max // n2 if n2 !=0 else range_max)
        if n1 == 0: n1 = n2

    return n1, n2

def gerar_pergunta(operacao: str, faixa_etaria: str) -> tuple[str | None, list[int] | None, int | None, str | None]:
    if operacao not in OPERACOES_SUPORTADAS:
        return None, None, None, "Operação não suportada."

    n1, n2 = gerar_numeros_pergunta(operacao, faixa_etaria)
    pergunta_texto = ""
    resposta_correta = 0

    simbolos = {"soma": "+", "subtracao": "-", "multiplicacao": "x", "divisao": "÷"}
    simbolo = simbolos.get(operacao)

    pergunta_texto = f"Quanto é {n1} {simbolo} {n2}?"

    if operacao == "soma": resposta_correta = n1 + n2
    elif operacao == "subtracao": resposta_correta = n1 - n2
    elif operacao == "multiplicacao": resposta_correta = n1 * n2
    elif operacao == "divisao":
        if n2 == 0: return None, None, None, "Erro: tentativa de divisao por zero ao gerar pergunta."
        resposta_correta = n1 // n2

    return pergunta_texto, [n1, n2], resposta_correta, None

def gerar_exemplo_pratico(operacao: str, faixa_etaria: str, numeros: list[int], resultado_correto: int, tentativa: int = 0) -> str:
    n1, n2 = numeros
    obj = obter_objeto_aleatorio(faixa_etaria)
    
    obj_n1_p = pluralizar(obj, n1)
    obj_n2_p = pluralizar(obj, n2)
    obj_res_p = pluralizar(obj, resultado_correto)
    
    exemplo = ""
    simbolo = {"soma": "+", "subtracao": "-", "multiplicacao": "x", "divisao": "÷"}.get(operacao)

    if operacao == "soma":
        if tentativa % 2 == 0:
            exemplo = f"Imagine que você tem {n1} {obj_n1_p}. Se você ganhar mais {n2} {obj_n2_p}, você terá {resultado_correto} {obj_res_p} ao todo! ( {n1} {simbolo} {n2} = {resultado_correto} )"
        else:
            exemplo = f"Pense em um cesto com {n1} {obj_n1_p}. Se colocarmos mais {n2} {obj_n2_p} lá dentro, o cesto agora tem {resultado_correto} {obj_res_p}. ( {n1} {simbolo} {n2} = {resultado_correto} )"
    elif operacao == "subtracao":
        if tentativa % 2 == 0:
            exemplo = f"Se você tem {n1} {obj_n1_p} e {n2} {obj_n2_p} são retirados (ou você deu para um amigo!), sobram {resultado_correto} {obj_res_p}. ( {n1} {simbolo} {n2} = {resultado_correto} )"
        else:
            exemplo = f"Havia {n1} {obj_n1_p} em uma prateleira. Se tirarmos {n2} {obj_n2_p}, restarão {resultado_correto} {obj_res_p} na prateleira. ( {n1} {simbolo} {n2} = {resultado_correto} )"
    elif operacao == "multiplicacao":
        pessoas_ou_grupos = pluralizar("grupo",n1) if n1 > 1 else "grupo" # ou "caixa", "pacote"
        if tentativa % 2 == 0:
            exemplo = f"Se você tem {n1} {pessoas_ou_grupos}, e em cada {obj} há {n2} {pluralizar(obj, n2)}, então no total você tem {n1} vezes {n2}, que é igual a {resultado_correto} {obj_res_p}. ( {n1} {simbolo} {n2} = {resultado_correto} )"
        else:
            exemplo = f"Multiplicar é somar repetidas vezes! {n1} {simbolo} {n2} significa somar o número {n2} por {n1} vezes. Se temos {n1} {pluralizar('conjunto',n1)} com {n2} {pluralizar(obj,n2)} cada, ao todo são {resultado_correto} {obj_res_p}."
    elif operacao == "divisao":
        if n2 == 0: return "Não podemos dividir por zero em um exemplo!" # Segurança
        pessoas_ou_partes = pluralizar("amigo",n2) if n2 > 1 else "amigo"
        if tentativa % 2 == 0:
            exemplo = f"Se você tem {n1} {obj_n1_p} e quer dividir igualmente entre {n2} {pessoas_ou_partes}, cada um receberá {resultado_correto} {pluralizar(obj, resultado_correto)}. ( {n1} {simbolo} {n2} = {resultado_correto} )"
        else:
            exemplo = f"Imagine {n1} {obj_n1_p} para serem guardados em {n2} {pluralizar('caixa',n2)} iguais. Em cada caixa caberão {resultado_correto} {pluralizar(obj, resultado_correto)}. ( {n1} {simbolo} {n2} = {resultado_correto} )"

    return exemplo if exemplo else "Desculpe, não consegui pensar em um bom exemplo agora."

def salvar_log_csv():
    global estado_sessao
    log_final = {}
    log_final["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_final["id_sessao"] = estado_sessao["id_sessao"]
    log_final["faixa_etaria"] = estado_sessao["faixa_etaria_atual"]
    log_final["operacao_solicitada"] = estado_sessao["operacao_atual"]
    log_final["pergunta_gerada"] = estado_sessao["pergunta_atual_texto"]
    log_final["numeros_pergunta"] = str(estado_sessao["pergunta_atual_numeros"])
    log_final["resposta_correta"] = estado_sessao["resposta_correta_pergunta"]
    
    log_final.update(estado_sessao["log_interacao_atual"])

    df_linha = pd.DataFrame([log_final])
    
    for col in CSV_HEADERS:
        if col not in df_linha.columns:
            df_linha[col] = None
    df_linha = df_linha[CSV_HEADERS]

    if not os.path.exists(CSV_FILE):
        df_linha.to_csv(CSV_FILE, index=False, header=True, encoding='utf-8-sig')
    else:
        df_linha.to_csv(CSV_FILE, mode='a', index=False, header=False, encoding='utf-8-sig')
    
    estado_sessao["log_interacao_atual"] = {}


@app.post("/aprender_matematica")
async def aprender_matematica(data: AlunoInput):
    global estado_sessao

    if data.acao == "iniciar_aprendizado":
        if not data.operacao or not data.faixa_etaria:
            return {"erro": "Operação e faixa etária são obrigatórias para iniciar."}
        
        op_lower = data.operacao.lower()
        if op_lower not in OPERACOES_SUPORTADAS:
            return {"erro": f"Operação '{data.operacao}' não suportada. Tente: {', '.join(OPERACOES_SUPORTADAS)}"}

        estado_sessao["id_sessao"] = estado_sessao.get("id_sessao") or datetime.now().strftime("%Y%m%d%H%M%S%f")
        estado_sessao["operacao_atual"] = op_lower
        estado_sessao["faixa_etaria_atual"] = data.faixa_etaria
        estado_sessao["tentativas_exemplo_atual"] = 0
        estado_sessao["log_interacao_atual"] = {}

        pergunta, numeros, resp_correta, erro_geracao = gerar_pergunta(op_lower, data.faixa_etaria)
        if erro_geracao: return {"erro": erro_geracao}

        estado_sessao["pergunta_atual_texto"] = pergunta
        estado_sessao["pergunta_atual_numeros"] = numeros
        estado_sessao["resposta_correta_pergunta"] = resp_correta
        
        return {
            "mensagem": f"Olá! Vamos aprender sobre {op_lower}.",
            "pergunta": pergunta,
            "id_sessao_debug": estado_sessao["id_sessao"]
        }

    elif data.acao == "enviar_resposta":
        if not estado_sessao["operacao_atual"] or not estado_sessao["pergunta_atual_texto"]:
            return {"erro": "Nenhuma pergunta ativa. Por favor, inicie o aprendizado ('iniciar_aprendizado')."}
        if data.resposta_aluno is None: return {"erro": "Por favor, envie sua resposta."}

        try:
            resp_aluno_num = float(data.resposta_aluno.replace(",", "."))
        except ValueError:
            return {"erro": "Sua resposta deve ser um número (ex: 10 ou 3.5)."}

        estado_sessao["log_interacao_atual"]["resposta_aluno"] = resp_aluno_num
        correta = (resp_aluno_num == estado_sessao["resposta_correta_pergunta"])
        estado_sessao["log_interacao_atual"]["acertou_pergunta"] = correta
        
        msg_feedback = "Isso mesmo, resposta correta!" if correta else f"Quase! A resposta correta era {estado_sessao['resposta_correta_pergunta']}."
        
        estado_sessao["tentativas_exemplo_atual"] = 0
        exemplo = gerar_exemplo_pratico(
            estado_sessao["operacao_atual"], estado_sessao["faixa_etaria_atual"],
            estado_sessao["pergunta_atual_numeros"], estado_sessao["resposta_correta_pergunta"],
            estado_sessao["tentativas_exemplo_atual"]
        )
        estado_sessao["ultimo_exemplo_fornecido"] = exemplo
        estado_sessao["log_interacao_atual"][f"exemplo_fornecido_{estado_sessao['tentativas_exemplo_atual'] + 1}"] = exemplo

        return {
            "feedback_resposta": msg_feedback,
            "exemplo_pratico": exemplo,
            "pergunta_feedback": "Você entendeu este exemplo? (Responda com 'sim' [true] ou 'não' [false])"
        }

    elif data.acao == "enviar_feedback_exemplo":
        if not estado_sessao["ultimo_exemplo_fornecido"]:
             return {"erro": "Nenhum exemplo foi fornecido ainda para dar feedback."}
        if data.feedback_entendeu is None:
            return {"erro": "Por favor, envie seu feedback (true para sim, false para não)."}

        num_tentativa_atual_log = estado_sessao["tentativas_exemplo_atual"] + 1
        estado_sessao["log_interacao_atual"][f"entendeu_exemplo_{num_tentativa_atual_log}"] = data.feedback_entendeu
        
        if data.feedback_entendeu:
            salvar_log_csv()
            msg_proximo = (f"Que bom que você entendeu! Gostaria de tentar outra pergunta de {estado_sessao['operacao_atual']} "
                           f"ou aprender uma nova operação? Use a ação 'iniciar_aprendizado'.")
            estado_sessao["pergunta_atual_texto"] = None 
            return {"mensagem": msg_proximo, "proxima_acao_sugerida": "iniciar_aprendizado"}
        else:
            estado_sessao["tentativas_exemplo_atual"] += 1
            if estado_sessao["tentativas_exemplo_atual"] < MAX_TENTATIVAS_EXEMPLO:
                novo_exemplo = gerar_exemplo_pratico(
                    estado_sessao["operacao_atual"], estado_sessao["faixa_etaria_atual"],
                    estado_sessao["pergunta_atual_numeros"], estado_sessao["resposta_correta_pergunta"],
                    estado_sessao["tentativas_exemplo_atual"]
                )
                estado_sessao["ultimo_exemplo_fornecido"] = novo_exemplo
                estado_sessao["log_interacao_atual"][f"exemplo_fornecido_{estado_sessao['tentativas_exemplo_atual'] + 1}"] = novo_exemplo
                return {
                    "mensagem": "Ok, vamos tentar explicar de outra forma!",
                    "novo_exemplo_pratico": novo_exemplo,
                    "pergunta_feedback": "E este novo exemplo, você entendeu? (Responda com 'sim' [true] ou 'não' [false])"
                }
            else:
                salvar_log_csv()
                msg_final_tentativa = ("Sinto muito que ainda não esteja claro. "
                                       "Seus esforços são importantes! Que tal tentarmos uma nova pergunta sobre este tópico ou mudar de assunto? "
                                       "Use a ação 'iniciar_aprendizado'.")
                estado_sessao["pergunta_atual_texto"] = None
                return {"mensagem": msg_final_tentativa, "proxima_acao_sugerida": "iniciar_aprendizado"}
    else:
        return {"erro": "Ação desconhecida. Use 'iniciar_aprendizado', 'enviar_resposta' ou 'enviar_feedback_exemplo'."}