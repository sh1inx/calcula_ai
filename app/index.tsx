import { Ionicons } from "@expo/vector-icons";
import React, { useState, useEffect, useRef } from "react";
import { ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View, Keyboard, KeyboardAvoidingView, Platform } from "react-native";
import ApiService from '@/services/api.service';

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
  ml_fator_aplicado_debug?: number | string;
}

export default function Index() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ text: string, author: 'user' | 'bot' }[]>([]);
  
  const [estadoConversa, setEstadoConversa] = useState<EstadoConversa>("INICIAL");
  const [operacaoSelecionada, setOperacaoSelecionada] = useState<string | null>(null);
  const [faixaEtariaSelecionada, setFaixaEtariaSelecionada] = useState<string | null>(null);

  const scrollViewRef = useRef<ScrollView>(null);

  useEffect(() => {
    adicionarMensagemBot("Olá! Bem-vindo ao Calcula Aí! Qual operação matemática você gostaria de aprender hoje? (Ex: soma, subtração, multiplicação, divisão)");
    setEstadoConversa("PEDINDO_OPERACAO");
  }, []);

  useEffect(() => {
    scrollViewRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const adicionarMensagemBot = (texto: string) => {
    setMessages(prev => [...prev, { text: texto, author: 'bot' }]);
  };

  const resetarFluxoAprendizadoCompleto = (mensagemErro?: string) => {
    if (mensagemErro) {
        adicionarMensagemBot(mensagemErro);
    }
    adicionarMensagemBot("Vamos tentar novamente do início. Qual operação matemática você gostaria de aprender? (Ex: soma, subtração)");
    setEstadoConversa("PEDINDO_OPERACAO");
    setOperacaoSelecionada(null);
    setFaixaEtariaSelecionada(null); 
  };

  const resetarParaNovaOperacao = (mensagem?: string) => {
    if (mensagem) {
        adicionarMensagemBot(mensagem);
    }
    adicionarMensagemBot("Qual operação você gostaria de aprender agora?");
    setEstadoConversa("PEDINDO_OPERACAO");
    setOperacaoSelecionada(null);
  };

    const handleSend = async () => {
    if (!input.trim()) return;

    const userInputText = input.trim();
    setMessages(prev => [...prev, { text: userInputText, author: 'user' }]);
    setInput("");
    Keyboard.dismiss();

    let dataParaEnviarNaRequisicao: any = null;
    let deveFazerChamadaAPI = true;

    try {
        switch (estadoConversa) {
            case "PEDINDO_OPERACAO":
                const operacaoInput = userInputText.toLowerCase();
                const operacoesValidas = ["soma", "subtração", "subtracao", "multiplicação", "multiplicacao", "divisão", "divisao"];
                if (!operacoesValidas.includes(operacaoInput)) {
                    adicionarMensagemBot("Operação inválida. Por favor, escolha entre: soma, subtração, multiplicação ou divisão.");
                    deveFazerChamadaAPI = false;
                } else {
                    const operacaoNormalizada = operacaoInput.replace("ç", "c").replace("ã", "a");
                    setOperacaoSelecionada(operacaoNormalizada);

                    if (faixaEtariaSelecionada) { 
                        dataParaEnviarNaRequisicao = {
                            acao: "iniciar_aprendizado",
                            operacao: operacaoNormalizada,
                            faixa_etaria: faixaEtariaSelecionada, 
                        };
                    } else { 
                        setEstadoConversa("PEDINDO_FAIXA_ETARIA");
                        adicionarMensagemBot(`Entendido, vamos aprender sobre ${operacaoNormalizada}! Agora, por favor, informe sua idade (ex: 7).`);
                        deveFazerChamadaAPI = false; 
                    }
                }
                break;

            case "PEDINDO_FAIXA_ETARIA":
                const idadeInput = userInputText.trim();
                let faixaEtariaParaAPI = "";

                if (!/^\d+$/.test(idadeInput)) {
                    adicionarMensagemBot("Por favor, informe sua idade como um número (ex: 7).");
                    deveFazerChamadaAPI = false;
                } else {
                    const idade = parseInt(idadeInput, 10);

                    if (idade >= 3 && idade <= 5) faixaEtariaParaAPI = "3-5";
                    else if (idade >= 6 && idade <= 8) faixaEtariaParaAPI = "6-8";
                    else if (idade >= 9 && idade <= 12) faixaEtariaParaAPI = "9-12";
                    else if (idade >= 13 && idade <= 15) faixaEtariaParaAPI = "13-15";
                    else if (idade >= 16 && idade <= 18) faixaEtariaParaAPI = "16-18";
                    else if (idade >= 19 && idade <= 22) faixaEtariaParaAPI = "19-22";
                    else if (idade >= 23 && idade <= 25) faixaEtariaParaAPI = "23-25";
                    else {
                        adicionarMensagemBot("Desculpe, no momento só temos conteúdo para idades entre 3 e 25 anos. Vamos tentar de novo com uma idade válida?");
                        deveFazerChamadaAPI = false;
                    }

                    if (deveFazerChamadaAPI) {
                        setFaixaEtariaSelecionada(faixaEtariaParaAPI); 
                        dataParaEnviarNaRequisicao = {
                            acao: "iniciar_aprendizado",
                            operacao: operacaoSelecionada, 
                            faixa_etaria: faixaEtariaParaAPI,
                        };
                    }
                }
                break; 

            case "AGUARDANDO_RESPOSTA_PERGUNTA":
                dataParaEnviarNaRequisicao = {
                    acao: "enviar_resposta",
                    resposta_aluno: userInputText,
                };
                break; 

            case "AGUARDANDO_FEEDBACK_EXEMPLO":
                const feedbackEntendeu = userInputText.toLowerCase() === 'sim' || userInputText.toLowerCase() === 'true';
                dataParaEnviarNaRequisicao = {
                    acao: "enviar_feedback_exemplo",
                    feedback_entendeu: feedbackEntendeu
                };
                break;
            
            default:
                resetarFluxoAprendizadoCompleto("Estado de conversa desconhecido. Vamos recomeçar.");
                deveFazerChamadaAPI = false;
        }

        if (deveFazerChamadaAPI && dataParaEnviarNaRequisicao) { 
            const respostaDoBackend = await api.post<AprendizadoApiResponseData>(API_ENDPOINT, dataParaEnviarNaRequisicao);
            const aprendizadoData: AprendizadoApiResponseData | null = respostaDoBackend;

            if (aprendizadoData?.ml_fator_aplicado_debug) {
                console.log("ML Fator Aplicado (Debug):", aprendizadoData.ml_fator_aplicado_debug);
            }

            if (!aprendizadoData) {
                resetarFluxoAprendizadoCompleto("Não recebi uma resposta estruturada do servidor.");
                return;
            }

            if (aprendizadoData.erro) {
                adicionarMensagemBot(`Erro do servidor: ${aprendizadoData.erro}`);
                if (dataParaEnviarNaRequisicao.acao === "iniciar_aprendizado") {
                     resetarFluxoAprendizadoCompleto(); 
                } else {
                    resetarParaNovaOperacao("Houve um problema. Que tal tentarmos uma nova operação?");
                }
                return; 
            }
            
            if (dataParaEnviarNaRequisicao.acao === "iniciar_aprendizado") {
                 if (aprendizadoData.pergunta) {
                    if (aprendizadoData.mensagem) adicionarMensagemBot(aprendizadoData.mensagem);
                    adicionarMensagemBot(aprendizadoData.pergunta);
                    setEstadoConversa("AGUARDANDO_RESPOSTA_PERGUNTA");
                } else {
                    resetarFluxoAprendizadoCompleto("Não consegui carregar a pergunta. Vamos tentar de novo.");
                }
            } else if (dataParaEnviarNaRequisicao.acao === "enviar_resposta") {
                if (aprendizadoData.feedback_resposta && aprendizadoData.exemplo_pratico && aprendizadoData.pergunta_feedback) {
                    adicionarMensagemBot(aprendizadoData.feedback_resposta);
                    adicionarMensagemBot(aprendizadoData.exemplo_pratico);
                    adicionarMensagemBot(aprendizadoData.pergunta_feedback);
                    setEstadoConversa("AGUARDANDO_FEEDBACK_EXEMPLO");
                } else {
                     resetarParaNovaOperacao("Não recebi um feedback completo. Vamos tentar outra operação?");
                }
            } else if (dataParaEnviarNaRequisicao.acao === "enviar_feedback_exemplo") {
                 if (aprendizadoData.mensagem) adicionarMensagemBot(aprendizadoData.mensagem);

                if (aprendizadoData.novo_exemplo_pratico) {
                    adicionarMensagemBot(aprendizadoData.novo_exemplo_pratico);
                    if (aprendizadoData.pergunta_feedback) {
                        adicionarMensagemBot(aprendizadoData.pergunta_feedback);
                    } else {
                        resetarParaNovaOperacao("Algo inesperado ocorreu com o exemplo. Vamos tentar uma nova operação?");
                    }
                } else { 
                    if (aprendizadoData.proxima_acao_sugerida === "iniciar_aprendizado") {
                        resetarParaNovaOperacao(); 
                    } else {
                        if (!aprendizadoData.mensagem) {
                             adicionarMensagemBot("Concluímos por aqui. Se quiser, pode escolher uma nova operação!");
                        }
                        resetarParaNovaOperacao(); 
                    }
                }
            }
        } else if (deveFazerChamadaAPI && !dataParaEnviarNaRequisicao) {
            console.error("Erro interno: dados para API deveriam ter sido preparados mas não foram.", estadoConversa, dataParaEnviarNaRequisicao);
            resetarFluxoAprendizadoCompleto("Ocorreu um erro interno ao preparar os dados.");
        }
    } catch (error: any) {
        console.error("Erro na chamada da API:", error);
        let errorMessage = "Desculpe, ocorreu um erro ao processar sua solicitação.";
        if (error.response && error.response.data && (error.response.data.msg || error.response.data.erro)) {
            errorMessage = error.response.data.msg || error.response.data.erro;
        } else if (error.message) {
            errorMessage = error.message;
        }
        resetarFluxoAprendizadoCompleto(errorMessage);
    }
};
    
  const getPlaceholder = () => {
    switch (estadoConversa) {
      case "PEDINDO_OPERACAO":
        return "Digite a operação (soma, subtração, ...)";
      case "PEDINDO_FAIXA_ETARIA":
        return "Qual sua idade (ex: 7)?"; 
      case "AGUARDANDO_RESPOSTA_PERGUNTA":
        return "Digite sua resposta numérica aqui:";
      case "AGUARDANDO_FEEDBACK_EXEMPLO":
        return "Entendeu o exemplo? (sim/não):";
      default:
        return "Digite sua mensagem...";
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
        keyboardVerticalOffset={Platform.OS === "ios" ? 64 : 0} 
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
            keyboardType={
                estadoConversa === "PEDINDO_FAIXA_ETARIA" || estadoConversa === "AGUARDANDO_RESPOSTA_PERGUNTA" 
                ? "numeric" 
                : "default"
            }
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
    paddingTop: Platform.OS === 'ios' ? 50 : 30, 
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
    paddingHorizontal: 15, 
    paddingVertical: 10, 
    borderTopWidth: 1,
    borderColor: "#ddd",
    backgroundColor: '#fff', 
    alignItems: "center",
    paddingBottom: Platform.OS === 'ios' ? 25 : 10, 
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