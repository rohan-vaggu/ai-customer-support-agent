import { useState, useEffect, useRef } from "react";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: "bot",
      text: "Hello! How can I help you?",
    },
  ]);

  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [theme, setTheme] = useState("dark");

  const messagesEndRef = useRef(null);

  const apiUrl = "/chat";

  // Load theme from localStorage on component mount
  useEffect(() => {
    const savedTheme = localStorage.getItem("chatbot-theme") || "dark";
    setTheme(savedTheme);
  }, []);

  // Auto Scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isTyping]);

  // Toggle theme and save to localStorage
  const toggleTheme = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    localStorage.setItem("chatbot-theme", newTheme);
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userInput = input;

    // Add user message
    const userMessage = {
      id: Date.now(),
      sender: "user",
      text: userInput,
    };

    setMessages((prev) => [...prev, userMessage]);

    setInput("");

    // Show typing indicator
    setIsTyping(true);

    try {
      // Extract conversation history (skip initial greeting, keep last 10 messages for richer context)
      const conversationHistory = messages
        .slice(1) // Skip initial bot greeting
        .slice(-10) // Keep last 10 messages for better context window
        .map((msg) => ({
          sender: msg.sender,
          text: msg.text,
        }));

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: userInput,
          history: conversationHistory,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();

        throw new Error(
          `Backend error: ${errorText || response.statusText}`
        );
      }

      const data = await response.json();

      // Hide typing indicator
      setIsTyping(false);

      // Add bot response
      const botMessage = {
        id: Date.now() + 1,
        sender: "bot",
        text:
          data.response ||
          "No response received from server.",
      };

      setMessages((prev) => [...prev, botMessage]);

    } catch (error) {
      console.error("Error:", error);

      // Hide typing indicator
      setIsTyping(false);

      const errorMessage = {
        id: Date.now() + 2,
        sender: "bot",
        text:
          error?.message ||
          "Unable to connect to server.",
      };

      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={`app ${theme === "light" ? "light-mode" : ""}`}>
      <div className="chat-box">
        <div className="header">
          <h1>AI Support Chat</h1>
          <button 
            className="theme-toggle" 
            onClick={toggleTheme}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>

        <div className="messages">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.sender}`}
            >
              {message.text}
            </div>
          ))}

          {/* Typing Indicator */}
          {isTyping && (
            <div className="message bot">
              typing...
            </div>
          )}

          {/* Auto Scroll Target */}
          <div ref={messagesEndRef}></div>
        </div>

        <div className="input-area">
          <input
            type="text"
            placeholder="Type your message..."
            value={input}
            onChange={(e) =>
              setInput(e.target.value)
            }
            onKeyDown={handleKeyPress}
          />

          <button onClick={handleSend}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;