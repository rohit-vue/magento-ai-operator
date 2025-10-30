// src/app/page.js
"use client";

import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { FaPaperPlane, FaPlus, FaFileUpload, FaUser, FaRobot, FaClipboardList, FaComments, FaStore } from 'react-icons/fa';

// --- API Endpoints ---
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL
const CHAT_API_URL = `${API_BASE_URL}/api/v1/chatbot/chat`;
const UPLOAD_API_URL = `${API_BASE_URL}/api/v1/files/upload`;
const CONNECT_API_URL = `${API_BASE_URL}/api/v1/auth/connect`;


// --- Child Component Definitions ---
const ProductCard = ({ product }) => ( <div className="product-card"> <img src={product.image_url ? product.image_url : "https://placehold.co/400x400/374151/F9FAFB?text=No+Image"} alt={product.name} className="product-card-image" /> <div className="product-card-content"> <h3 className="product-card-name">{product.name}</h3> <p className="product-card-price" dangerouslySetInnerHTML={{ __html: product.price || 'Price not available' }} /> <p className="product-card-description">{(product.description || '').substring(0, 100)}{(product.description || '').length > 100 ? '...' : ''}</p> </div> </div> );
const ProductGrid = ({ products }) => ( <div className="product-grid-container"> {products.map(product => <ProductCard key={product.id || product.sku} product={product} />)} </div> );
const ThinkingIndicator = () => ( <div className="message-wrapper bot"> <div className="message-icon"><FaRobot /></div> <div className="thinking-indicator"> <span></span><span></span><span></span> </div> </div> );
const Message = ({ sender, text, data, intent }) => { const isBot = sender === 'bot'; const products = (intent === 'search_products_result' && Array.isArray(data)) ? data : null; return ( <div className={`message-wrapper ${sender}`}> <div className="message-icon">{isBot ? <FaRobot /> : <FaUser />}</div> <div className="message-content"> <p style={{ margin: 0, whiteSpace: 'pre-wrap' }} dangerouslySetInnerHTML={{ __html: text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} /> {products && <ProductGrid products={products} />} </div> </div> ); };
const WelcomeScreen = () => ( <div className="welcome-container"> <div className="welcome-icon"><FaRobot /></div> <h1 className="welcome-title">Magento AI Operator</h1> <p className="welcome-subtitle">Your intelligent assistant for managing your e-commerce store.</p> </div> );
const ConnectionPanel = ({ onConnect, isConnecting, connectionStatus }) => { const [details, setDetails] = useState({ store_url: '', consumer_key: '', consumer_secret: '', access_token: '', access_token_secret: '' }); const handleChange = (e) => { setDetails({ ...details, [e.target.name]: e.target.value }); }; const handleSubmit = (e) => { e.preventDefault(); onConnect(details); }; return ( <form onSubmit={handleSubmit} className="connection-panel"> <div className="form-group"> <label htmlFor="store_url">Store URL</label> <input type="text" id="store_url" name="store_url" value={details.store_url} onChange={handleChange} placeholder="https://your-magento.com" required /> </div> <div className="form-group"> <label htmlFor="consumer_key">Consumer Key</label> <input type="password" id="consumer_key" name="consumer_key" value={details.consumer_key} onChange={handleChange} required /> </div> <div className="form-group"> <label htmlFor="consumer_secret">Consumer Secret</label> <input type="password" id="consumer_secret" name="consumer_secret" value={details.consumer_secret} onChange={handleChange} required /> </div> <div className="form-group"> <label htmlFor="access_token">Access Token</label> <input type="password" id="access_token" name="access_token" value={details.access_token} onChange={handleChange} required /> </div> <div className="form-group"> <label htmlFor="access_token_secret">Access Token Secret</label> <input type="password" id="access_token_secret" name="access_token_secret" value={details.access_token_secret} onChange={handleChange} required /> </div> <button type="submit" className="connect-btn" disabled={isConnecting}> {isConnecting ? 'Connecting...' : 'Connect to Store'} </button> {connectionStatus.message && ( <div className={`connection-status ${connectionStatus.type}`}> {connectionStatus.message} </div> )} </form> ); };
const ConnectionStatus = ({ storeName, onDisconnect }) => ( <div className="connection-status-display"> <p>Status: <span>Connected</span></p> <p>Store: <span>{storeName}</span></p> <button className="disconnect-btn" onClick={onDisconnect}>Disconnect</button> </div> );

// --- Main Page Component ---
export default function HomePage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [credentials, setCredentials] = useState(null);
  const [lastBotData, setLastBotData] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState({ type: '', message: '' });
  const [storeName, setStoreName] = useState('');

  const scrollToBottom = () => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); };
  useEffect(scrollToBottom, [messages, isLoading]);

  const handleConnect = async (creds) => { setIsConnecting(true); setConnectionStatus({ type: '', message: '' }); try { const response = await axios.post(CONNECT_API_URL, creds); setConnectionStatus({ type: 'success', message: response.data.message }); setStoreName(response.data.store_name); setCredentials(creds); setIsConnected(true); } catch (error) { const errorMsg = error.response?.data?.detail || "Failed to connect."; setConnectionStatus({ type: 'error', message: errorMsg }); setIsConnected(false); } finally { setIsConnecting(false); } };
  const handleDisconnect = () => { setIsConnected(false); setStoreName(''); setCredentials(null); setLastBotData(null); setConnectionStatus({ type: '', message: '' }); setMessages([{ sender: 'bot', text: 'Successfully disconnected from the store.' }]); };
  const handleSendMessage = async (userInput) => { if (!userInput.trim()) return; const newMessages = [...messages, { sender: 'user', text: userInput }]; setMessages(newMessages); setInput(''); setIsLoading(true); try { const response = await axios.post(CHAT_API_URL, { user_id: 'user_123', message: userInput, credentials: credentials, context: lastBotData, }); const { response_text, intent, data } = response.data; setLastBotData(data || null); setMessages([...newMessages, { sender: 'bot', text: response_text, intent: intent, data: data }]); } catch (error) { const errorText = error.response?.data?.detail || "An unexpected error occurred."; setMessages([...newMessages, { sender: 'bot', text: errorText }]); } finally { setIsLoading(false); } };
  const handleFileUpload = async (event) => { const file = event.target.files[0]; if (!file) return; const newMessages = [...messages, { sender: 'user', text: `Uploading file: ${file.name}` }]; setMessages(newMessages); setIsLoading(true); const formData = new FormData(); formData.append('file', file); try { const response = await axios.post(UPLOAD_API_URL, formData, { headers: { 'Content-Type': 'multipart/form-data' } }); setMessages([...newMessages, { sender: 'bot', text: response.data.message }]); } catch (error) { const errorText = error.response?.data?.detail || "File upload failed."; setMessages([...newMessages, { sender: 'bot', text: errorText }]); } finally { setIsLoading(false); event.target.value = null; } };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-content">
          <h2 className="sidebar-title"><FaComments /> Chat Sessions</h2>
          <button className="new-chat-button"><FaPlus /> New Chat</button>
        </div>
      </aside>

      <main className="chat-area">
        {messages.length === 0 && !isLoading ? <WelcomeScreen /> : (
          <div className="chat-messages">
            {messages.map((msg, index) => <Message key={index} {...msg} />)}
            {isLoading && <ThinkingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
        <div className="chat-input-area">
          <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(input); }} className="chat-input-form">
            {/* --- THIS IS THE CORRECTED ORDER --- */}
            <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden-file-input" accept=".csv,.jpg,.jpeg,.png"/>
            
            {/* The text input and file upload button are now in the middle */}
            <button type="button" className="icon-button" onClick={() => fileInputRef.current.click()} disabled={isLoading || !isConnected} aria-label="Upload file"><FaFileUpload /></button>
            <input type="text" className="chat-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder={isConnected ? "Search for products by keyword, brand, or SKU..." : "Please connect to a store first."} disabled={isLoading || !isConnected} />
            
            {/* The submit button is now the LAST element, but visually it stays on the right */}
            <button type="submit" className="icon-button" disabled={!input.trim() || isLoading || !isConnected}><FaPaperPlane /></button>
          </form>
        </div>
      </main>

       <aside className="right-sidebar">
        <div className="sidebar-content">
          <h2 className="sidebar-title">
            {isConnected ? <><FaClipboardList /> Action Panel</> : <><FaStore /> Store Connection</>}
            <span className={`connection-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
          </h2>
          {isConnected ? (
              <>
                  <ConnectionStatus storeName={storeName} onDisconnect={handleDisconnect} />
                  <p className="sidebar-placeholder" style={{textAlign: 'center', color: 'var(--text-color-secondary)', fontSize: '0.9rem'}}>Future actions will appear here.</p>
              </>
          ) : (
              <ConnectionPanel onConnect={handleConnect} isConnecting={isConnecting} connectionStatus={connectionStatus} />
          )}
        </div>
      </aside>
    </div>
  );
}