import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { ApiResponseInterface } from '@/interfaces/backend.response.interface';
import ApiService from '@/services/api.service';

const api = new ApiService();

export default function Index() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ text: string, author: string }[]>([]);

  const handleSend = async () => {
    setMessages((prev) => [...prev, { text: input, author: 'user' }]);

    setInput('');

    try {
      const response = await api.post<ApiResponseInterface>("http://192.168.0.9:8000/processar", { valor: input });
      if (response) {
        const data = response;
        console.log(data);
        setMessages((prev) => [...prev, { text: data.valor, author: 'bot' }]);
      }
    } catch (error) {
      console.error(error);
      setMessages((prev) => [...prev, { text: "Erro ao processar a expressão.", author: 'bot' }]);
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Ionicons name="calculator-outline" size={35} color="#fff" style={{ marginRight: 90, textAlign: "center" }} />
        <Text style={styles.headerText}>Calcula Aí</Text>
      </View>

      {/* Chat area */}
      <ScrollView style={styles.chatArea} contentContainerStyle={{ padding: 16 }}>
        {messages.map((msg, index) => (
          <View
            key={index}
            style={[
              styles.messageBubble,
              msg.author === 'user' ? styles.userBubble : styles.botBubble
            ]}
          >
            <Text style={styles.messageText}>{msg.text}</Text>
          </View>
        ))}
      </ScrollView>

      {/* Input area */}
      <View style={styles.inputArea}>
        <TextInput
          style={styles.textInput}
          placeholder="Digite uma expressão:"
          value={input}
          onChangeText={setInput}
        />
        <TouchableOpacity style={styles.sendButton} onPress={handleSend}>
          <Text style={{ color: "#fff", fontWeight: "bold" }}>Enviar</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  header: {
    backgroundColor: "#F27C29",
    paddingTop: 50,
    paddingBottom: 26,
    paddingHorizontal: 20,
    flexDirection: "row",
    alignItems: "center",
  },
  headerText: { color: "#fff", fontSize: 30, fontWeight: "bold" },
  chatArea: { flex: 1, backgroundColor: "#fff" },
  messageBubble: {
    padding: 10,
    borderRadius: 16,
    marginVertical: 4,
    maxWidth: "70%",
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: "#FBB77D",
  },
  botBubble: {
    alignSelf: "flex-start",
    backgroundColor: "#eee",
  },
  messageText: {
    fontSize: 16,
  },
  inputArea: {
    flexDirection: "row",
    padding: 20,
    borderTopWidth: 1,
    borderColor: "#ddd",
    alignItems: "center",
    marginBottom: 12,
  },
  textInput: {
    flex: 1,
    backgroundColor: "#f5f5f5",
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 10,
    marginRight: 20,
  },
  sendButton: {
    backgroundColor: "#007bff",
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 20,
  },
});