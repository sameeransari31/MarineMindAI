import React, { useState, useRef, useEffect } from 'react';
import { Box, Container, Typography, TextField, IconButton, Paper, CircularProgress, Button } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import './RagChat.css';


const TypingIndicator = () => {
    return (
        <motion.div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <motion.span
                style={{ width: 8, height: 8, backgroundColor: 'currentColor', borderRadius: '50%' }}
                animate={{ y: [0, -4, 0] }}
                transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.span
                style={{ width: 8, height: 8, backgroundColor: 'currentColor', borderRadius: '50%' }}
                animate={{ y: [0, -4, 0] }}
                transition={{ duration: 1, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
            />
            <motion.span
                style={{ width: 8, height: 8, backgroundColor: 'currentColor', borderRadius: '50%' }}
                animate={{ y: [0, -4, 0] }}
                transition={{ duration: 1, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
            />
        </motion.div>
    );
};


function getSessionId() {
    let sessionId = localStorage.getItem('rag_session_id');
    if (!sessionId) {
        sessionId = `session_${Date.now()}`;
        localStorage.setItem('rag_session_id', sessionId);
    }
    return sessionId;
}


function RagChat() {

  const [sessionId] = useState(getSessionId());
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [documentUploaded, setDocumentUploaded] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [fileName, setFileName] = useState("");
  const chatEndRef = useRef(null);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  const handleFileChange = async (event) => {
    const file = event.target.files[0]; if (!file) return;
    setIsUploading(true); setFileName(file.name); setMessages([{ text: `Uploading and processing "${file.name}"... This may take a moment.`, sender: 'ai' }]);
    const formData = new FormData(); formData.append('file', file); formData.append('session_id', sessionId);
    try {
        const response = await fetch('http://localhost:8000/rag/upload', { method: 'POST', body: formData });
        if (!response.ok) { const errorData = await response.json(); throw new Error(errorData.detail || "File processing failed."); }
        setDocumentUploaded(true); setMessages([{ text: `Processing complete! You can now ask questions about "${file.name}".`, sender: 'ai' }]);
    } catch (error) { setMessages([{ text: `Sorry, the file could not be processed. Error: ${error.message}`, sender: 'ai' }]);
    } finally { setIsUploading(false); }
  };
  const handleSendMessage = async (e) => {
    e.preventDefault(); if (!input.trim() || isLoading) return;
    const userMessage = { text: input, sender: "user" }; setMessages(prev => [...prev, userMessage]); setInput(""); setIsLoading(true);
    try {
        const response = await fetch('http://localhost:8000/rag/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: userMessage.text, session_id: sessionId }), });
        if (!response.ok) { const errorData = await response.json(); throw new Error(errorData.detail || `API error`); }
        const data = await response.json();
        const formatApiResponse = (apiResponse) => {
            let formattedText = `**${apiResponse.problem_summary}**\n\n`;
            if (apiResponse.remediation_steps?.length > 0) {
                formattedText += "**Recommended Steps:**\n";
                apiResponse.remediation_steps.forEach(step => { formattedText += `${step.step}. ${step.action}\n`; });
            }
            if (apiResponse.safety_summary) { formattedText += `\n**Safety Note:** ${apiResponse.safety_summary}`; }
            return formattedText;
        };
        const aiMessage = { text: formatApiResponse(data), sender: "ai" }; setMessages(prev => [...prev, aiMessage]);
    } catch (error) { const errorMessage = { text: `An error occurred: ${error.message}`, sender: "ai" }; setMessages(prev => [...prev, errorMessage]);
    } finally { setIsLoading(false); }
  };
  const renderUploadView = () => {
    return (<Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" height="100%">
        <Typography variant="h5" gutterBottom>Upload Document to Begin</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>Please upload a PDF manual to start your session.</Typography>
        <Button variant="contained" component="label" startIcon={<UploadFileIcon />} disabled={isUploading}>
            {isUploading ? 'Processing...' : 'Choose PDF File'}
            <input type="file" hidden onChange={handleFileChange} accept=".pdf" />
        </Button>
        {isUploading && <CircularProgress sx={{ mt: 2 }} />}
    </Box>);
  };


  const renderChatView = () => (
    <Box display="flex" flexDirection="column" height="100%">
      <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 2 }}>
        {messages.map((msg, index) => (
          <Paper key={index} elevation={3} className={`message ${msg.sender}`}>
            <ReactMarkdown>{msg.text}</ReactMarkdown>
          </Paper>
        ))}
        {/* Replace CircularProgress with our new TypingIndicator */}
        {isLoading && (
            <Paper elevation={3} className="message ai">
                <TypingIndicator />
            </Paper>
        )}
        <div ref={chatEndRef} />
      </Box>
      <Box component="form" onSubmit={handleSendMessage} sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
          {/* ... (TextField remains the same) ... */}
        <TextField fullWidth variant="outlined" placeholder="Ask a question..." value={input} onChange={(e) => setInput(e.target.value)} disabled={isLoading} InputProps={{ endAdornment: (<IconButton type="submit" color="primary" disabled={isLoading}> <SendIcon /> </IconButton>), }} />
      </Box>
    </Box>
  );


  return (
    <Container maxWidth="md" sx={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column', p: 0 }}>
        <Paper elevation={4} sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h5" component="h1">MarineMind AI</Typography>
            {documentUploaded && <Typography color="text.secondary">Chatting about: <strong>{fileName}</strong></Typography>}
        </Paper>
        <Box sx={{ flexGrow: 1, height: '100%', overflow: 'hidden' }}>
            {documentUploaded ? renderChatView() : renderUploadView()}
        </Box>
    </Container>
  );
}

export default RagChat;