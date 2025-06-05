from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import random
import os
from datetime import datetime
import joblib

MODELO_DIFICULDADE_PATH = "modelo_fator_dificuldade.pkl"
PREPROCESSADOR_FEATURES_PATH = "preprocessador_features.pkl"

modelo_dificuldade = None
preprocessador_features = None

try:
    modelo_dificuldade = joblib.load(MODELO_DIFICULDADE_PATH)
    print(f"INFO: Modelo de dificuldade '{MODELO_DIFICULDADE_PATH}' carregado com sucesso.")
except FileNotFoundError:
    print(f"AVISO: Arquivo do modelo de dificuldade '{MODELO_DIFICULDADE_PATH}' não encontrado. Usando lógica de dificuldade padrão.")
except Exception as e:
    print(f"ERRO: Não foi possível carregar o modelo de dificuldade: {e}. Usando lógica de dificuldade padrão.")


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
    "log_interacao_atual": {},
    "historico_respostas_sessao": [],
    "perguntas_respondidas_total_sessao": 0,
    "acertos_total_sessao": 0,
    "ml_fator_dificuldade_aplicado": 1.0,
    "ml_features_usadas": {}
}

CSV_FILE = "aprendizado_log.csv"
CSV_HEADERS = [
    "timestamp", "id_sessao", "faixa_etaria", "operacao_solicitada",
    "pergunta_gerada", "numeros_pergunta", "resposta_aluno", "resposta_correta", "acertou_pergunta",
    "exemplo_fornecido_1", "entendeu_exemplo_1",
    "exemplo_fornecido_2", "entendeu_exemplo_2",
    "exemplo_fornecido_3", "entendeu_exemplo_3",

    "ml_fator_dificuldade_aplicado",
    "ml_taxa_acerto_recente",
    "ml_perguntas_na_op_atual"
]

OBJETOS_POR_FAIXA = {
    "3-5": ["maçã", "bola", "gatinho", "carrinho", "doce", "flor"],
    "6-8": ["lápis", "figurinha", "moeda", "livro", "bala", "borracha"],
    "9-12": ["jogo", "dinheiro (real)", "página", "adesivo", "minuto", "ponto (em jogo)"],
    "13-15": ["byte", "pixel", "ação (financeira)", "molécula", "quilômetro", "voto", "linha de código"],
    "16-18": ["crédito (universitário)", "hora de estudo", "percentual de desconto", "artigo científico", "projeto (escolar)", "questão (prova)"],
    "19-22": ["parcela (financiamento)", "caloria (dieta)", "investimento (R$)", "tarefa (freelance)", "meta (de poupança)", "semestre (universitário)"],
    "23-25": ["despesa (mensal)", "receita (vendas)", "imposto (%)", "m² (metro quadrado)", "cliente (projeto)", "objetivo (de carreira)"],
    "padrao": ["item", "unidade", "ponto", "valor"]
}
OPERACOES_SUPORTADAS = ["soma", "subtracao", "multiplicacao", "divisao"]
NUM_EXEMPLO_VARIATIONS = 3
MAX_TENTATIVAS_EXEMPLO = NUM_EXEMPLO_VARIATIONS

def obter_objeto_aleatorio(faixa_etaria: str) -> str:
    objetos = OBJETOS_POR_FAIXA.get(faixa_etaria, OBJETOS_POR_FAIXA["padrao"])
    return random.choice(objetos)

def pluralizar(palavra: str, quantidade: int) -> str:
    if quantidade == 1: return palavra
    if palavra.endswith('ão'): return palavra[:-2] + 'ões'
    elif palavra.endswith('m'): return palavra[:-1] + 'ns'
    elif palavra.endswith(('r', 's', 'z')): return palavra + 'es'
    elif palavra.endswith(tuple('aeiouln')): return palavra + "s"
    else: return palavra + 's'

def extrair_features_aluno(estado_sessao_atual: dict) -> dict:
    features = {
        "taxa_acerto_geral_sessao": 0.0,
        "taxa_acerto_recente_op_sessao": 0.0,
        "perguntas_respondidas_op_sessao": 0,
        "faixa_etaria_inicio_num": 0,
    }

    if estado_sessao_atual.get("perguntas_respondidas_total_sessao", 0) > 0:
        features["taxa_acerto_geral_sessao"] = estado_sessao_atual.get("acertos_total_sessao", 0) / estado_sessao_atual["perguntas_respondidas_total_sessao"]

    op_atual = estado_sessao_atual.get("operacao_atual")
    hist_respostas = estado_sessao_atual.get("historico_respostas_sessao", [])
    
    respostas_op_atual = [r for r in hist_respostas if r.get("op") == op_atual]
    features["perguntas_respondidas_op_sessao"] = len(respostas_op_atual)

    if features["perguntas_respondidas_op_sessao"] > 0:
        ultimas_n_respostas_op = respostas_op_atual[-5:]
        acertos_recentes_op = sum(1 for r in ultimas_n_respostas_op if r.get("acertou"))
        if ultimas_n_respostas_op:
             features["taxa_acerto_recente_op_sessao"] = acertos_recentes_op / len(ultimas_n_respostas_op)

    faixa_str = estado_sessao_atual.get("faixa_etaria_atual", "0-0")
    try:
        features["faixa_etaria_inicio_num"] = int(faixa_str.split('-')[0])
    except:
        features["faixa_etaria_inicio_num"] = 0 

    print(f"DEBUG: Features extraídas para ML: {features}")
    return features

def gerar_numeros_pergunta(operacao: str, faixa_etaria: str, estado_sessao_atual: dict) -> tuple[int, int]:
    n1, n2 = 0, 0
    fator_dificuldade_ml = 1.0
    estado_sessao_atual["ml_fator_dificuldade_aplicado"] = fator_dificuldade_ml
    estado_sessao_atual["ml_features_usadas"] = {}


    if modelo_dificuldade:
        features_para_modelo = extrair_features_aluno(estado_sessao_atual)
        estado_sessao_atual["ml_features_usadas"] = features_para_modelo

        try:
            df_para_predicao = pd.DataFrame([features_para_modelo])
            
            predicao_fator = modelo_dificuldade.predict(df_para_predicao)[0]
            
            fator_dificuldade_ml = max(0.5, min(float(predicao_fator), 1.5)) 
            estado_sessao_atual["ml_fator_dificuldade_aplicado"] = fator_dificuldade_ml
            print(f"INFO: ML previu fator de dificuldade: {predicao_fator}, aplicado: {fator_dificuldade_ml}")
        except Exception as e:
            print(f"ERRO: Falha ao usar modelo de ML para prever dificuldade: {e}. Usando fator padrão 1.0.")
           

    range_max_base = 5
    if faixa_etaria == "6-8": range_max_base = 10
    elif faixa_etaria == "9-12": range_max_base = 25
    elif faixa_etaria == "13-15": range_max_base = 75
    elif faixa_etaria == "16-18": range_max_base = 150
    elif faixa_etaria == "19-22": range_max_base = 300
    elif faixa_etaria == "23-25": range_max_base = 600
    else: range_max_base = 20

    range_max = int(range_max_base * fator_dificuldade_ml)
    range_max = max(5, range_max)
    print(f"DEBUG: Range max base: {range_max_base}, Fator ML: {fator_dificuldade_ml}, Range max final: {range_max}")

    n1_min = 1
    n2_min = 1
    if faixa_etaria in ["19-22", "23-25"] and fator_dificuldade_ml >= 1:
        n1_min = random.choice([int(10*fator_dificuldade_ml), int(20*fator_dificuldade_ml), int(5*fator_dificuldade_ml)])
        n2_min = random.choice([int(5*fator_dificuldade_ml), int(10*fator_dificuldade_ml), int(1*fator_dificuldade_ml)])
        n1_min = max(1, n1_min)
        n2_min = max(1, n2_min)

    n1 = random.randint(n1_min, range_max if range_max >= n1_min else n1_min + 1)
    n2 = random.randint(n2_min, range_max if range_max >= n2_min else n2_min + 1)
    
    if operacao in ["multiplicacao", "divisao"]:
        mult_div_n1_max_base = range_max_base // 10 if range_max_base > 50 else range_max_base // 5
        mult_div_n2_max_base = 10 if faixa_etaria not in ["19-22", "23-25"] else 20
        
        mult_div_n1_max = int(mult_div_n1_max_base * fator_dificuldade_ml)
        mult_div_n2_max = int(mult_div_n2_max_base * fator_dificuldade_ml)

        mult_div_n1_max = max(n1_min +1 , mult_div_n1_max)
        mult_div_n2_max = max(n2_min +1 , mult_div_n2_max)


        if faixa_etaria == "3-5":
            n1 = random.randint(1, int(5 * fator_dificuldade_ml) if fator_dificuldade_ml > 0.8 else 5)
            n2 = random.randint(1, int(3 * fator_dificuldade_ml) if fator_dificuldade_ml > 0.8 else 3)
            n1 = max(1,n1); n2 = max(1,n2)
        else:
            n1 = random.randint(n1_min, mult_div_n1_max if mult_div_n1_max >= n1_min else n1_min +1)
            n2 = random.randint(n2_min, mult_div_n2_max if mult_div_n2_max >= n2_min else n2_min +1)

    if operacao == "subtracao":
        if n1 < n2: n1, n2 = n2, n1
        if n1 == n2 and n1 > 0 : n1 += random.randint(1, max(1, int(range_max // 10 * fator_dificuldade_ml)))
        elif n1 == n2 and n1 == 0:
            n1 = random.randint(1, max(1, int(range_max // 10 * fator_dificuldade_ml)))
        n1=max(0,n1); n2=max(0,n2)
            
    if operacao == "divisao":
        if n2 == 0: n2 = 1 
        if n2 == 1 and faixa_etaria not in ["3-5", "6-8"] and range_max > 5 :
             n2_temp = random.randint(2, max(3, min(10, int(range_max // 10 * fator_dificuldade_ml))))
             n2 = max(1, n2_temp)


        max_quociente_base = 10
        if faixa_etaria == "3-5": max_quociente_base = 4
        elif faixa_etaria in ["9-12", "13-15"]: max_quociente_base = 15
        elif faixa_etaria in ["16-18", "19-22", "23-25"]: max_quociente_base = 25
        
        max_quociente = int(max_quociente_base * fator_dificuldade_ml)
        max_quociente = max(1, max_quociente)

        quociente = random.randint(1, max_quociente)
        n1 = n2 * quociente

        if n1 == 0 and n2 != 0: n1 = n2
       
        if n1 > (range_max_base * fator_dificuldade_ml * 1.2) and n2 > 1:
            n2_new = random.randint(1, max(1, n2 // 2))
            n1 = n2_new * quociente
            if n1 != 0 : n2 = n2_new

    n1=max(0,n1); n2=max(0,n2 if operacao != 'divisao' else (1 if n2==0 else n2) )
    return n1, n2

def gerar_pergunta(operacao: str, faixa_etaria: str, estado_sessao_atual: dict) -> tuple[str | None, list[int] | None, int | None, str | None]:
    if operacao not in OPERACOES_SUPORTADAS:
        return None, None, None, "Operação não suportada."

    n1, n2 = gerar_numeros_pergunta(operacao, faixa_etaria, estado_sessao_atual)
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

def obter_personagem_aleatorio(faixa_etaria: str, usar_voce_chance=0.3) -> tuple[str, str, str]:
    if random.random() < usar_voce_chance: return "você", "você", "tem"
    personagens_base = [("Ana", "ela", "tem"), ("Léo", "ele", "tem"), ("Bia", "ela", "tem"), ("um colega", "ele", "tem"), ("uma startup", "ela", "tem"), ("um cliente", "ele", "tem"), ("a equipe", "ela", "tem")]
    personagens_contextuais = [("o estudante", "ele", "tem"), ("a pesquisadora", "ela", "tem"), ("o gerente de projetos", "ele", "tem"), ("a consultora financeira", "ela", "tem"), ("um investidor", "ele", "tem"), ("uma empresa", "ela", "tem")]
    if faixa_etaria in ["3-5", "6-8"]: escolha = random.choice([p for p in personagens_base if p[0] not in ["uma startup", "um cliente", "a equipe"]])
    elif faixa_etaria in ["9-12", "13-15"]: escolha = random.choice(personagens_base[:4] + personagens_contextuais[:2])
    elif faixa_etaria in ["16-18", "19-22"]: escolha = random.choice(personagens_base + personagens_contextuais[:4])
    else: escolha = random.choice(personagens_base + personagens_contextuais)
    return escolha

def obter_elementos_soma(faixa_etaria: str) -> tuple[str, str]:
    verbos_ganho = ["ganhou", "recebeu", "adicionou", "acumulou", "obteve", "conseguiu"]
    locais_acumulo = ["em sua conta", "em seu portfólio", "ao seu orçamento", "no total de vendas", "como bônus", "de lucro", "em sua poupança", "para o projeto"]
    if faixa_etaria in ["3-5", "6-8", "9-12"]:
        verbos_ganho = ["ganhou", "achou", "recebeu", "coletou", "juntou"]
        locais_acumulo = ["em sua coleção", "em seu cofrinho", "na cesta", "na prateleira", "em sua mochila"]
    elif faixa_etaria in ["13-15", "16-18"]:
        verbos_ganho.extend(["economizou", "adquiriu"])
        locais_acumulo.extend(["para sua viagem", "em créditos de jogo", "em sua mesada"])
    return random.choice(verbos_ganho), random.choice(locais_acumulo)

def obter_elementos_subtracao(faixa_etaria: str) -> tuple[str, str]:
    verbos_perda = ["perdeu", "gastou", "retirou", "deduziu", "utilizou", "pagou"]
    locais_origem = ["de sua conta", "de seu orçamento", "do investimento inicial", "para as despesas", "como imposto", "do saldo disponível", "para cobrir um custo"]
    if faixa_etaria in ["3-5", "6-8", "9-12"]:
        verbos_perda = ["perdeu", "deu", "usou", "comeu", "tirou"]
        locais_origem = ["de sua coleção", "de sua caixa", "da prateleira", "do pacote", "do total que tinha"]
    elif faixa_etaria in ["13-15", "16-18"]:
        verbos_perda.extend(["consumiu", "emprestou"])
        locais_origem.extend(["de seus créditos", "da mensalidade", "para um amigo"])
    return random.choice(verbos_perda), random.choice(locais_origem)

def obter_elementos_multi_div(faixa_etaria: str) -> tuple[str, str, str]:
    grupos_plural_base = ["caixas", "pacotes", "grupos", "lotes", "conjuntos"]
    if faixa_etaria in ["3-5", "6-8", "9-12"]: grupos_plural = ["cestas", "saquinhos", "equipes (de amigos)", "fileiras (de brinquedos)"] + grupos_plural_base[:2]
    elif faixa_etaria in ["13-15", "16-18"]: grupos_plural = ["turmas", "disciplinas", "experimentos", "capítulos"] + grupos_plural_base[:3]
    else: grupos_plural = ["departamentos", "projetos", "campanhas", "ações (da empresa)", "contratos", "relatórios"] + grupos_plural_base
    grupos_singular = [g[:-1] if g.endswith("s") and g != "ações (da empresa)" and not g.endswith("ens") else g.replace(" (de amigos)","").replace(" (de brinquedos)","") for g in grupos_plural]
    grupos_singular = [s.replace("ações (da empresa)", "ação (da empresa)") for s in grupos_singular]
    idx = random.randrange(len(grupos_plural)); g_plural = grupos_plural[idx]; g_singular = grupos_singular[idx]
    distribuicao_templates = [f"em cada {g_singular}", f"por {g_singular}", f"para cada {g_singular}", "em cada unidade", "contido em cada um(a)"]
    if faixa_etaria in ["19-22", "23-25"]: distribuicao_templates.extend([f"alocado(a) por {g_singular}", f"designado(a) para cada {g_singular}"])
    return g_plural, g_singular, random.choice(distribuicao_templates)

def gerar_exemplo_pratico(operacao: str, faixa_etaria: str, numeros: list[int], resultado_correto: int, tentativa_idx: int = 0) -> str:
    n1, n2 = numeros
    obj_original = obter_objeto_aleatorio(faixa_etaria)
    obj_n1_p = pluralizar(obj_original, n1)
    obj_n2_p = pluralizar(obj_original, n2 if n2 != 0 else 1) if n2 != 0 else f"0 {obj_original}"
    if resultado_correto == 0:
        if faixa_etaria in ["3-5", "6-8", "9-12"]:
             obj_res_p_txt = f"nenhum(a) {obj_original}" if not obj_original.endswith("s") and not '(' in obj_original else f"nenhum {obj_original}"
             if '(' in obj_original: obj_res_p_txt = f"nenhum valor de {obj_original}"
        else: obj_res_p_txt = f"0 {pluralizar(obj_original, 0)}"
    else: obj_res_p_txt = f"{resultado_correto} {pluralizar(obj_original, resultado_correto)}"
    exemplo = ""; simbolo = {"soma": "+", "subtracao": "-", "multiplicacao": "x", "divisao": "÷"}.get(operacao)
    personagem_nome, personagem_pronome, personagem_verbo_ter = obter_personagem_aleatorio(faixa_etaria)
    variation_style = tentativa_idx % NUM_EXEMPLO_VARIATIONS
    if operacao == "soma":
        verbo_s, contexto_s = obter_elementos_soma(faixa_etaria)
        if variation_style == 0: exemplo = f"Considere que {personagem_nome} já {personagem_verbo_ter} {n1} {obj_n1_p}. Se {personagem_pronome} {verbo_s} mais {n2} {obj_n2_p if n2 !=0 else 'nada'}, {personagem_pronome} passará a ter {obj_res_p_txt} {contexto_s}."
        elif variation_style == 1:
            outro_p_nome, _, _ = obter_personagem_aleatorio(faixa_etaria, usar_voce_chance=0.05) 
            exemplo = f"Se {personagem_nome} possui {n1} {obj_n1_p} e {outro_p_nome} transfere mais {n2} {obj_n2_p if n2 !=0 else 'nenhum ' + obj_original} para {personagem_pronome}, {personagem_nome} ficará com {obj_res_p_txt}."
        else: 
            local_generico = random.choice(['um saldo', 'um total', 'um montante', 'um relatório', 'uma planilha']) if faixa_etaria not in ["3-5","6-8","9-12"] else random.choice(['um cesto', 'um pote', 'um saco'])
            exemplo = f"Imagine {local_generico} inicial de {n1} {obj_n1_p}. Adicionando {n2} {obj_n2_p if n2 !=0 else 'zero ' + obj_original}, o novo {local_generico.split(' ')[-1]} será de {obj_res_p_txt}."
    elif operacao == "subtracao":
        if n1 < n2 and faixa_etaria in ["3-5", "6-8", "9-12"]: exemplo = f"Se {personagem_nome} tem apenas {n1} {obj_n1_p}, não é possível tirar {n2} {obj_n2_p}. Precisaria de mais! Matematicamente, o resultado seria {resultado_correto}, indicando uma falta."
        elif n1 < n2: exemplo = f"Se {personagem_nome} tem um saldo de {n1} {obj_n1_p} e precisa deduzir {n2} {obj_n2_p}, o resultado será {obj_res_p_txt}, indicando um déficit ou valor negativo."
        else:
            verbo_sub, contexto_sub = obter_elementos_subtracao(faixa_etaria)
            if variation_style == 0: exemplo = f"{personagem_nome} {personagem_verbo_ter} {n1} {obj_n1_p}. Após {verbo_sub} {n2} {obj_n2_p} {contexto_sub}, {personagem_pronome} restará com {obj_res_p_txt}."
            elif variation_style == 1:
                local_origem_generico = random.choice(['um estoque', 'um orçamento', 'uma reserva']) if faixa_etaria not in ["3-5","6-8","9-12"] else random.choice(['uma prateleira', 'uma caixa', 'uma gaveta'])
                exemplo = f"Havia {n1} {obj_n1_p} em {local_origem_generico}. Se {n2} {pluralizar(obj_original, n2)} foram {random.choice(['removidos', 'utilizados', 'retirados'])}, restaram {obj_res_p_txt}."
            else:
                verbo_acao = random.choice(["precisa pagar", "tem uma despesa de", "investiu"]) if faixa_etaria not in ["3-5","6-8","9-12"] else "precisa usar"
                exemplo = f"Se {personagem_nome} {verbo_acao} {n2} {obj_n2_p} de um total disponível de {n1} {obj_n1_p}, sobrarão {obj_res_p_txt}."
    elif operacao == "multiplicacao":
        g_plural, g_singular, dist_template = obter_elementos_multi_div(faixa_etaria)
        obj_n2_fmt = f"{n2} {pluralizar(obj_original, n2)}" if n2 != 0 else f"nenhum {obj_original}"
        if variation_style == 0: exemplo = f"Se {personagem_nome} possui {n1} {pluralizar(g_singular, n1)}, e {dist_template.replace(g_singular, '')} {random.choice(['contém', 'gera', 'vale', 'custa'])} {obj_n2_fmt}, então o valor total ou quantidade total que {personagem_pronome} tem é de {obj_res_p_txt}."
        elif variation_style == 1:
            acao_mult = random.choice(["adquiriu", "processou", "vendeu", "analisou"]) if faixa_etaria not in ["3-5","6-8","9-12"] else random.choice(["comprou", "organizou", "fez"])
            exemplo = f"{personagem_nome} {acao_mult} {n1} {pluralizar(g_singular, n1)}, cada um(a) associado(a) a {obj_n2_fmt}. Ao todo, isso representa {obj_res_p_txt}."
        else: exemplo = f"A operação de multiplicar {n1} por {n2} pode ser vista como somar o número {n2}, {n1} {pluralizar('vez',n1)}. Isso resulta em {obj_res_p_txt}."
    elif operacao == "divisao":
        if n2 == 0: return "Não podemos dividir por zero em um exemplo prático!"
        g_plural, g_singular, dist_template = obter_elementos_multi_div(faixa_etaria)
        if resultado_correto == 0 and n1 > 0 : obj_resultado_fmt = f"nenhum(a) {obj_original} completo(a) (sobrariam {n1 % n2 if n2!=0 else 0} {pluralizar(obj_original, n1 % n2 if n2!=0 else 0)})"
        else: obj_resultado_fmt = f"{resultado_correto} {pluralizar(obj_original, resultado_correto)}"
        entidade_divisao_singular = random.choice(["participante", "seção", g_singular, "beneficiário"]) if faixa_etaria not in ["3-5","6-8","9-12"] else random.choice(["amigo", "pessoa", "caixinha"])
        entidade_divisao_plural = pluralizar(entidade_divisao_singular, n2)
        if variation_style == 0: exemplo = f"Se {personagem_nome} possui {n1} {obj_n1_p} e deseja distribuir igualmente entre {n2} {entidade_divisao_plural}, cada {entidade_divisao_singular} receberá {obj_resultado_fmt}."
        elif variation_style == 1: exemplo = f"Imagine um total de {n1} {obj_n1_p} que precisam ser alocados em {n2} {pluralizar(g_singular, n2)} de forma equitativa. Cada {g_singular} comportará {obj_resultado_fmt}."
        else: exemplo = f"Dado um montante de {n1} {obj_n1_p}, se cada {g_singular} deve conter {n2} {pluralizar(obj_original,n2)}, é possível formar {obj_resultado_fmt} {pluralizar(g_singular, resultado_correto)} completos."
    if exemplo: exemplo += f" (Matematicamente: {n1} {simbolo} {n2} = {resultado_correto})"
    else: exemplo = "Desculpe, não consegui pensar em um bom exemplo para esta situação."
    return exemplo

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
    
    log_final["ml_fator_dificuldade_aplicado"] = estado_sessao.get("ml_fator_dificuldade_aplicado", 1.0)
    
    ml_features = estado_sessao.get("ml_features_usadas", {})
    log_final["ml_taxa_acerto_recente"] = ml_features.get("taxa_acerto_recente_op_sessao") 
    log_final["ml_perguntas_na_op_atual"] = ml_features.get("perguntas_respondidas_op_sessao") 

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
        
        faixas_validas = [f for f in OBJETOS_POR_FAIXA.keys() if f != "padrao"]
        if data.faixa_etaria not in faixas_validas:
            return {"erro": f"Faixa etária '{data.faixa_etaria}' não suportada. Tente uma das seguintes: {', '.join(faixas_validas)}"}

        if estado_sessao.get("id_sessao") != (estado_sessao.get("id_sessao") or datetime.now().strftime("%Y%m%d%H%M%S%f")) or \
           estado_sessao.get("operacao_atual") != op_lower or \
           estado_sessao.get("faixa_etaria_atual") != data.faixa_etaria:
            
            estado_sessao["historico_respostas_sessao"] = []
            estado_sessao["perguntas_respondidas_total_sessao"] = 0
            estado_sessao["acertos_total_sessao"] = 0
            print("INFO: Resetando histórico de ML da sessão devido a nova sessão/operação/faixa.")

        estado_sessao["id_sessao"] = estado_sessao.get("id_sessao") or datetime.now().strftime("%Y%m%d%H%M%S%f")
        estado_sessao["operacao_atual"] = op_lower
        estado_sessao["faixa_etaria_atual"] = data.faixa_etaria
        estado_sessao["tentativas_exemplo_atual"] = 0
        estado_sessao["log_interacao_atual"] = {}
        pergunta, numeros, resp_correta, erro_geracao = gerar_pergunta(op_lower, data.faixa_etaria, estado_sessao)
        if erro_geracao: return {"erro": erro_geracao}

        estado_sessao["pergunta_atual_texto"] = pergunta
        estado_sessao["pergunta_atual_numeros"] = numeros
        estado_sessao["resposta_correta_pergunta"] = resp_correta
        
        return {
            "mensagem": f"Olá! Vamos praticar {op_lower} com exemplos para a faixa etária de {data.faixa_etaria}.",
            "pergunta": pergunta,
            "id_sessao_debug": estado_sessao["id_sessao"],
            "ml_fator_aplicado_debug": estado_sessao.get("ml_fator_dificuldade_aplicado", "N/A")
        }

    elif data.acao == "enviar_resposta":
        if not estado_sessao.get("operacao_atual") or not estado_sessao.get("pergunta_atual_texto"):
            return {"erro": "Nenhuma pergunta ativa. Por favor, inicie o aprendizado ('iniciar_aprendizado')."}
        if data.resposta_aluno is None: return {"erro": "Por favor, envie sua resposta."}

        try:
            resp_aluno_num = float(data.resposta_aluno.replace(",", "."))
        except ValueError:
            return {"erro": "Sua resposta deve ser um número (ex: 10 ou 3.5)."}

        correta = (abs(resp_aluno_num - estado_sessao["resposta_correta_pergunta"]) < 1e-9)
        
        estado_sessao["log_interacao_atual"]["resposta_aluno"] = resp_aluno_num
        estado_sessao["log_interacao_atual"]["acertou_pergunta"] = correta
        
        estado_sessao["historico_respostas_sessao"].append({
            "numeros_pergunta": list(estado_sessao["pergunta_atual_numeros"]),
            "acertou": correta,
            "op": str(estado_sessao["operacao_atual"])
        })
        estado_sessao["perguntas_respondidas_total_sessao"] += 1
        if correta:
            estado_sessao["acertos_total_sessao"] += 1
        
        msg_feedback = "Correto!" if correta else f"Quase! A resposta correta era {estado_sessao['resposta_correta_pergunta']}."
        
        estado_sessao["tentativas_exemplo_atual"] = 0 
        exemplo = gerar_exemplo_pratico(
            estado_sessao["operacao_atual"], estado_sessao["faixa_etaria_atual"],
            estado_sessao["pergunta_atual_numeros"], estado_sessao["resposta_correta_pergunta"],
            tentativa_idx=estado_sessao["tentativas_exemplo_atual"]
        )
        estado_sessao["ultimo_exemplo_fornecido"] = exemplo
        estado_sessao["log_interacao_atual"][f"exemplo_fornecido_{estado_sessao['tentativas_exemplo_atual'] + 1}"] = exemplo

        return {
            "feedback_resposta": msg_feedback,
            "exemplo_pratico": exemplo,
            "pergunta_feedback": "Este exemplo ajudou a entender? (Responda com 'sim' ou 'não')"
        }

    elif data.acao == "enviar_feedback_exemplo":
        if not estado_sessao["ultimo_exemplo_fornecido"]:
             return {"erro": "Nenhum exemplo foi fornecido ainda para dar feedback."}
        if data.feedback_entendeu is None:
            return {"erro": "Por favor, envie seu feedback (true para sim, false para não)."}

        num_exemplo_log = estado_sessao["tentativas_exemplo_atual"] + 1
        estado_sessao["log_interacao_atual"][f"entendeu_exemplo_{num_exemplo_log}"] = data.feedback_entendeu
        
        if data.feedback_entendeu:
            salvar_log_csv()
            msg_proximo = (f"Ótimo! Fico feliz em ajudar. Gostaria de tentar outra pergunta de {estado_sessao['operacao_atual']} "
                           f"para a mesma faixa etária ({estado_sessao['faixa_etaria_atual']}) ou aprender uma nova operação? Use a ação 'iniciar_aprendizado'.")
            estado_sessao["pergunta_atual_texto"] = None 
            return {"mensagem": msg_proximo, "proxima_acao_sugerida": "iniciar_aprendizado"}
        else:
            estado_sessao["tentativas_exemplo_atual"] += 1 
            if estado_sessao["tentativas_exemplo_atual"] < MAX_TENTATIVAS_EXEMPLO:
                novo_exemplo = gerar_exemplo_pratico(
                    estado_sessao["operacao_atual"], estado_sessao["faixa_etaria_atual"],
                    estado_sessao["pergunta_atual_numeros"], estado_sessao["resposta_correta_pergunta"],
                    tentativa_idx=estado_sessao["tentativas_exemplo_atual"]
                )
                estado_sessao["ultimo_exemplo_fornecido"] = novo_exemplo
                estado_sessao["log_interacao_atual"][f"exemplo_fornecido_{estado_sessao['tentativas_exemplo_atual'] + 1}"] = novo_exemplo
                return {
                    "mensagem": "Entendido. Vamos tentar explicar de uma maneira diferente:",
                    "novo_exemplo_pratico": novo_exemplo,
                    "pergunta_feedback": "E agora, este novo exemplo ficou mais claro? (Responda com 'sim' ou 'não')"
                }
            else:
                salvar_log_csv()
                msg_final_tentativa = ("Puxa, parece que ainda não ficou totalmente claro. Não se preocupe, aprender leva tempo! "
                                       "Seus esforços são muito válidos. Que tal tentarmos uma nova pergunta sobre este tópico ou mudar de assunto? "
                                       "Use a ação 'iniciar_aprendizado'.")
                estado_sessao["pergunta_atual_texto"] = None
                return {"mensagem": msg_final_tentativa, "proxima_acao_sugerida": "iniciar_aprendizado"}
    else:
        return {"erro": "Ação desconhecida. As ações válidas são: 'iniciar_aprendizado', 'enviar_resposta' ou 'enviar_feedback_exemplo'."}
