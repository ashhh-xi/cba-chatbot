"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import FormattedMessage from "./components/FormattedMessage"

interface Message {
  sender: "user" | "ai"
  text: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!input.trim()) return

    const newMessage: Message = { sender: "user", text: input }
    setMessages((prev) => [...prev, newMessage])
    setInput("")
    setLoading(true)

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: input.trim(),
          conversation_id: "default",
        }),
      })

      if (!response.ok) {
        throw new Error("Failed to fetch response from backend")
      }

      const data = await response.json()
      const aiMessage: Message = { sender: "ai", text: data.answer }
      setMessages((prev) => [...prev, aiMessage])
    } catch (error) {
      console.error("Error sending message:", error)
      const errorMessage: Message = { sender: "ai", text: "❌ Error connecting to chatbot" }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-container">
      {/* Chat Window */}
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: msg.sender === "ai" ? 0.2 : 0 }}
            className={`message ${msg.sender}`}
          >
            {msg.sender === "ai" ? (
              <FormattedMessage text={msg.text} />
            ) : (
              msg.text
            )}
          </motion.div>
        ))}
        {loading && (
          <motion.div
            className="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ repeat: Infinity, duration: 1, repeatType: "reverse" }}
          >
            Thinking...
          </motion.div>
        )}
      </div>

      {/* Input Bar */}
      <motion.div
        className="chat-input"
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 120 }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about CBA products, fees, insurance..."
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <motion.button
          whileTap={{ scale: 0.9 }}
          whileHover={{ scale: 1.05 }}
          onClick={sendMessage}
          disabled={loading}
        >
          Send
        </motion.button>
      </motion.div>
    </div>
  )
}
