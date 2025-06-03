import { Ionicons } from "@expo/vector-icons";
import React, { useState, useEffect, useRef } from "react";
import { ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View, Keyboard, KeyboardAvoidingView, Platform } from "react-native";
import ApiService from '@/services/api.service';
import { ApiResponseInterface } from "@/interfaces/backend.response.interface";


const api = new ApiService();
const API_ENDPOINT = "http://192.168.0.9:8000/aprender_matematica";

type EstadoConversa = 
  | "INICIAL"
  | "PEDINDO_OPERACAO"
  | "PEDINDO_FAIXA_ETARIA"
  | "AGUARDANDO_RESPOSTA_PERGUNTA"
  | "AGUARDANDO_FEEDBACK_EXEMPLO";

interface AprendizadoApiResponseData {
  mensagem?: string;
  pergunta?: string;
  erro?: string;
  feedback_resposta?: string;
  exemplo_pratico?: string;
  pergunta_feedback?: string;
  novo_exemplo_pratico?: string;
  proxima_acao_sugerida?: string;
  id_sessao_debug?: string; 
}

export default function Index() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ text: string, author: 'user' | 'bot' }[]>([]);
  
  const [estadoConversa, setEstadoConversa] = useState<EstadoConversa>("INICIAL");
  const [operacaoSelecionada, setOperacaoSelecionada] = useState<string | null>(null);
  const [faixaEtariaSelecionada, setFaixaEtariaSelecionada] = useState<string | null>(null);

  const scrollViewRef = useRef<ScrollView>(null);

  useEffect(() => {
    setMessages([{ text: "Olá! Bem-vindo ao Calcula Aí! Qual operação matemática você gostaria de aprender hoje? (Ex: soma, subtração, multiplicação, divisão)", author: 'bot' }]);
    setEstadoConversa("PEDINDO_OPERACAO");
  }, []);

  useEffect(() => {
    scrollViewRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const adicionarMensagemBot = (texto: string) => {
    setMessages(prev => [...prev, { text: texto, author: 'bot' }]);
  };

  const resetarFluxoAprendizado = (mensagemErro?: string) => {
    if (mensagemErro) {
        adicionarMensagemBot(mensagemErro);
    }
    adicionarMensagemBot("Vamos tentar novamente. Qual operação matemática você gostaria de aprender? (Ex: soma, subtração)");
    setEstadoConversa("PEDINDO_OPERACAO");
    setOperacaoSelecionada(null);
    setFaixaEtariaSelecionada(null);
  };

    const handleSend = async () => {
    console.log("handleSend INÍCIO - Estado:", estadoConversa, "Input:", input);
    if (!input.trim()) return;

    const userInputText = input.trim();
    setMessages(prev => [...prev, { text: userInputText, author: 'user' }]);
    setInput("");
    Keyboard.dismiss();

    let dataParaEnviarNaRequisicao: any = null;
    let deveFazerChamadaAPI = true;


    try {

        console.log("Antes do Switch - Estado:", estadoConversa, "userInputText:", userInputText);
        switch (estadoConversa) {
            case "PEDINDO_OPERACAO":
                console.log("Switch: PEDINDO_OPERACAO");
                const operacao = userInputText.toLowerCase();
                const operacoesValidas = ["soma", "subtração", "subtracao", "multiplicação", "multiplicacao", "divisão", "divisao"];
                if (!operacoesValidas.includes(operacao)) {
                    adicionarMensagemBot("Operação inválida. Por favor, escolha entre: soma, subtração, multiplicação ou divisão.");
                    deveFazerChamadaAPI = false;
                } else {
                    setOperacaoSelecionada(operacao.replace("ç", "c").replace("ã", "a"));
                    setEstadoConversa("PEDINDO_FAIXA_ETARIA");
                    adicionarMensagemBot("Entendido! Agora, por favor, informe sua faixa etária (ex: 3-5, 6-8, 9-12).");
                    deveFazerChamadaAPI = false;
                }
                break;

            case "PEDINDO_FAIXA_ETARIA":
                console.log("Switch: PEDINDO_FAIXA_ETARIA");
                const idadeInput = userInputText.trim();
                let faixaEtariaParaAPI = "";

                if (!/^\d+$/.test(idadeInput)) {
                    adicionarMensagemBot("Por favor, informe sua idade como um número (ex: 7).");
                    deveFazerChamadaAPI = false;
                    break;
                }

                const idade = parseInt(idadeInput, 10);

                if (idade >= 3 && idade <= 5) {
                    faixaEtariaParaAPI = "3-5";
                } else if (idade >= 6 && idade <= 8) {
                    faixaEtariaParaAPI = "6-8";
                } else if (idade >= 9 && idade <= 12) {
                    faixaEtariaParaAPI = "9-12";
                } else {
                    adicionarMensagemBot("Desculpe, no momento só temos conteúdo para idades entre 3 e 12 anos.");
                    deveFazerChamadaAPI = false;
                    break;
                }

                setFaixaEtariaSelecionada(faixaEtariaParaAPI);
                dataParaEnviarNaRequisicao = {
                    acao: "iniciar_aprendizado",
                    operacao: operacaoSelecionada,
                    faixa_etaria: faixaEtariaParaAPI,
                };
                console.log("PEDINDO_FAIXA_ETARIA - dataParaEnviar:", dataParaEnviarNaRequisicao);
                break; 

            case "AGUARDANDO_RESPOSTA_PERGUNTA":
                console.log("Switch: AGUARDANDO_RESPOSTA_PERGUNTA");
                dataParaEnviarNaRequisicao = {
                    acao: "enviar_resposta",
                    resposta_aluno: userInputText
                };
                console.log("AGUARDANDO_RESPOSTA_PERGUNTA - dataParaEnviar:", dataParaEnviarNaRequisicao);
                break; 

            case "AGUARDANDO_FEEDBACK_EXEMPLO":
                console.log("Switch: AGUARDANDO_FEEDBACK_EXEMPLO");
                const feedbackEntendeu = userInputText.toLowerCase() === 'sim' || userInputText.toLowerCase() === 'true';
                dataParaEnviarNaRequisicao = {
                    acao: "enviar_feedback_exemplo",
                    feedback_entendeu: feedbackEntendeu
                };
                console.log("AGUARDANDO_FEEDBACK_EXEMPLO - dataParaEnviar:", dataParaEnviarNaRequisicao);
                break;
            
            default:
                console.log("Switch: DEFAULT");
                resetarFluxoAprendizado("Estado de conversa desconhecido.");
                deveFazerChamadaAPI = false;
        }

        console.log("Após Switch - deveFazerChamadaAPI:", deveFazerChamadaAPI, "dataParaEnviarNaRequisicao:", dataParaEnviarNaRequisicao);

        if (deveFazerChamadaAPI) {
            if (!dataParaEnviarNaRequisicao || Object.keys(dataParaEnviarNaRequisicao).length === 0) {
                console.error("Tentativa de chamada API sem dados definidos ou com dados nulos!", estadoConversa, dataParaEnviarNaRequisicao);
                resetarFluxoAprendizado("Erro interno: dados para API não foram preparados.");
                return;
            }

            console.log("Enviando para API:", dataParaEnviarNaRequisicao);
            const respostaDoBackend = await api.post<AprendizadoApiResponseData>(API_ENDPOINT, dataParaEnviarNaRequisicao);
            
            console.log("==========================================");
            console.log("Resposta do Backend (JSON direto):", JSON.stringify(respostaDoBackend, null, 2));
            console.log("==========================================");

            const aprendizadoData: AprendizadoApiResponseData | null = respostaDoBackend;

            if (!aprendizadoData) {
                resetarFluxoAprendizado("Não recebi uma resposta estruturada do servidor.");
                return;
            }

            if (aprendizadoData.erro) {
                adicionarMensagemBot(aprendizadoData.erro);
                return; 
            }
            
            if (dataParaEnviarNaRequisicao.acao === "iniciar_aprendizado") {
                 if (aprendizadoData.pergunta) {
                    adicionarMensagemBot(aprendizadoData.mensagem || `Vamos praticar ${dataParaEnviarNaRequisicao.operacao}!`);
                    adicionarMensagemBot(aprendizadoData.pergunta);
                    setEstadoConversa("AGUARDANDO_RESPOSTA_PERGUNTA");
                } else {
                    resetarFluxoAprendizado("Não consegui carregar a pergunta a partir dos dados recebidos.");
                }
            } else if (dataParaEnviarNaRequisicao.acao === "enviar_resposta") {
                if (aprendizadoData.feedback_resposta && aprendizadoData.exemplo_pratico && aprendizadoData.pergunta_feedback) {
                    adicionarMensagemBot(aprendizadoData.feedback_resposta);
                    adicionarMensagemBot(aprendizadoData.exemplo_pratico);
                    adicionarMensagemBot(aprendizadoData.pergunta_feedback);
                    setEstadoConversa("AGUARDANDO_FEEDBACK_EXEMPLO");
                } else {
                    resetarFluxoAprendizado("Não recebi um feedback completo a partir dos dados recebidos.");
                }
            } else if (dataParaEnviarNaRequisicao.acao === "enviar_feedback_exemplo") {
                 if (aprendizadoData.mensagem) adicionarMensagemBot(aprendizadoData.mensagem);

                if (aprendizadoData.novo_exemplo_pratico) {
                    adicionarMensagemBot(aprendizadoData.novo_exemplo_pratico);
                    if (aprendizadoData.pergunta_feedback) {
                        adicionarMensagemBot(aprendizadoData.pergunta_feedback);
                    } else {
                        resetarFluxoAprendizado("Vamos tentar uma nova pergunta sobre outro tema.");
                    }
                } else { 
                    if (aprendizadoData.proxima_acao_sugerida === "iniciar_aprendizado") {
                        adicionarMensagemBot("Qual operação você gostaria de aprender agora?");
                        setEstadoConversa("PEDINDO_OPERACAO");
                        setOperacaoSelecionada(null);
                        setFaixaEtariaSelecionada(null);
                    } else if (!dataParaEnviarNaRequisicao.feedback_entendeu && !aprendizadoData.novo_exemplo_pratico) {
                        adicionarMensagemBot("Gostaria de tentar outra operação ou uma nova pergunta sobre o mesmo tópico?");
                        setEstadoConversa("PEDINDO_OPERACAO");
                        setOperacaoSelecionada(null);
                        setFaixaEtariaSelecionada(null);
                    } else if (dataParaEnviarNaRequisicao.feedback_entendeu && !aprendizadoData.novo_exemplo_pratico) {
                        adicionarMensagemBot("Ótimo! Qual operação você gostaria de aprender agora?");
                        setEstadoConversa("PEDINDO_OPERACAO");
                        setOperacaoSelecionada(null);
                        setFaixaEtariaSelecionada(null);
                    }
                }
            }
        }
    } catch (error: any) {
        console.error("Erro na chamada da API:", error);
        let errorMessage = "Desculpe, ocorreu um erro ao processar sua solicitação.";
        if (error.response && error.response.data && (error.response.data.msg || error.response.data.erro)) {
            errorMessage = error.response.data.msg || error.response.data.erro;
        } else if (error.message) {
            errorMessage = error.message;
        }
        resetarFluxoAprendizado(errorMessage);
    }
};
    
  const getPlaceholder = () => {
    switch (estadoConversa) {
      case "PEDINDO_OPERACAO":
        return "Digite a operação (soma, subtração, ...):";
      case "PEDINDO_FAIXA_ETARIA":
        return "Qual sua faixa etária (Ex: 3-5, 6-8, 9-12)?";
      case "AGUARDANDO_RESPOSTA_PERGUNTA":
        return "Digite sua resposta numérica aqui:";
      case "AGUARDANDO_FEEDBACK_EXEMPLO":
        return "Entendeu o exemplo? (sim/não):";
      default:
        return "Digite sua mensagem:";
    }
  };

  return (
    <View style={styles.container}> 
      <View style={styles.header}>
        <Ionicons name="calculator-outline" size={35} color="#fff" style={{ marginRight: 10 }} />
        <Text style={styles.headerText}>Calcula Aí</Text>
      </View>

      <KeyboardAvoidingView 
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={{ flex: 1 }}
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
      >
        <ScrollView 
          ref={scrollViewRef}
          style={styles.chatArea} 
          contentContainerStyle={styles.chatContentContainer}
          keyboardShouldPersistTaps="handled"
        >
          {messages.map((msg, index) => (
            <View
              key={index}
              style={[
                styles.messageBubble,
                msg.author === 'user' ? styles.userBubble : styles.botBubble
              ]}
            >
              <Text style={msg.author === 'user' ? styles.userMessageText : styles.botMessageText}>
                {msg.text}
              </Text>
            </View>
          ))}
        </ScrollView>

        <View style={styles.inputArea}>
          <TextInput
            style={styles.textInput}
            placeholder={getPlaceholder()}
            value={input}
            onChangeText={setInput}
            onSubmitEditing={handleSend}
            blurOnSubmit={false} 
          />
          <TouchableOpacity style={styles.sendButton} onPress={handleSend}>
            <Ionicons name="send-outline" size={24} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F0F0F0" }, 
  header: {
    backgroundColor: "#F27C29",
    paddingTop: 50, 
    paddingBottom: 20,
    paddingHorizontal: 20,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center", 
  },
  headerText: { color: "#fff", fontSize: 28, fontWeight: "bold" },
  chatArea: { flex: 1, backgroundColor: "#fff" },
  chatContentContainer: { paddingVertical: 16, paddingHorizontal: 10 },
  messageBubble: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 20, 
    marginVertical: 5,
    maxWidth: "80%", 
    shadowColor: "#000", 
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.1,
    shadowRadius: 1.00,
    elevation: 1,
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: "#FBB77D",
    borderBottomRightRadius: 5, 
  },
  botBubble: {
    alignSelf: "flex-start",
    backgroundColor: "#E5E5EA", 
    borderBottomLeftRadius: 5, 
  },
  userMessageText: {
    fontSize: 16,
    color: "#333", 
  },
  botMessageText: {
    fontSize: 16,
    color: "#000", 
  },
  inputArea: {
    flexDirection: "row",
    padding: 15, 
    borderTopWidth: 1,
    borderColor: "#ddd",
    backgroundColor: '#fff', 
    alignItems: "center",
    paddingBottom: 25, 
  },
  textInput: {
    flex: 1,
    backgroundColor: "#f0f0f0", 
    borderRadius: 25, 
    paddingHorizontal: 20,
    paddingVertical: 12,
    marginRight: 10, 
    fontSize: 16,
  },
  sendButton: {
    backgroundColor: "#007AFF", 
    padding: 12, 
    borderRadius: 25, 
    justifyContent: 'center',
    alignItems: 'center',
  },
});