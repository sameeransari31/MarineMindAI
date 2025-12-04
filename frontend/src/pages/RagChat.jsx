import React, { useState, useRef, useEffect } from 'react';
import { 
    Box, Container, Typography, TextField, IconButton, Paper, 
    CircularProgress, Button, Drawer, List, ListItem, ListItemText, 
    ListItemButton, Divider, Toolbar, AppBar, Dialog, DialogTitle, 
    DialogContent, DialogActions
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import AddIcon from '@mui/icons-material/Add';
import MenuIcon from '@mui/icons-material/Menu';
import DeleteIcon from '@mui/icons-material/Delete';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import './RagChat.css';

const API_BASE_URL = 'http://localhost:8000/rag';

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

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
}

function RagChat() {
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [sessionId, setSessionId] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [documentUploaded, setDocumentUploaded] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [fileName, setFileName] = useState("");
    const [loadingSessions, setLoadingSessions] = useState(true);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [sessionToDelete, setSessionToDelete] = useState(null);
    const chatEndRef = useRef(null);
    
    const drawerWidth = 280;

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Load sessions on mount
    useEffect(() => {
        loadSessions();
    }, []);

    // Load conversation history when session changes
    useEffect(() => {
        if (sessionId) {
            loadConversationHistory(sessionId);
        }
    }, [sessionId]);

    const loadSessions = async (skipAutoCreate = false) => {
        try {
            setLoadingSessions(true);
            const response = await fetch(`${API_BASE_URL}/sessions`);
            if (!response.ok) throw new Error('Failed to load sessions');
            const data = await response.json();
            const sessionsList = data.sessions || [];
            setSessions(sessionsList);
            
            // Create default session if none exists (only on initial load)
            if (!skipAutoCreate && sessionsList.length === 0 && !sessionId) {
                const newResponse = await fetch(`${API_BASE_URL}/sessions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                if (newResponse.ok) {
                    const newData = await newResponse.json();
                    setSessionId(newData.session_id);
                    // Reload sessions without auto-create to avoid loop
                    return await loadSessions(skipAutoCreate=true);
                }
            } else if (sessionsList.length > 0 && !sessionId) {
                // Set default session if none selected
                setSessionId(sessionsList[0].session_id);
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
        } finally {
            setLoadingSessions(false);
        }
    };

    const loadConversationHistory = async (sid) => {
        try {
            const response = await fetch(`${API_BASE_URL}/sessions/${sid}/history`);
            if (!response.ok) throw new Error('Failed to load history');
            const data = await response.json();
            setMessages(data.messages || []);
            setDocumentUploaded(data.has_document || false);
        } catch (error) {
            console.error('Error loading conversation history:', error);
            setMessages([]);
            setDocumentUploaded(false);
        }
    };

    const createNewSession = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            if (!response.ok) throw new Error('Failed to create session');
            const data = await response.json();
            const newSessionId = data.session_id;
            
            // Switch to new session
            setSessionId(newSessionId);
            setMessages([]);
            setDocumentUploaded(false);
            setFileName("");
            
            // Reload sessions (skip auto-create to avoid loop)
            await loadSessions(skipAutoCreate=true);
        } catch (error) {
            console.error('Error creating session:', error);
            alert('Failed to create new session');
        }
    };

    const switchSession = async (sid) => {
        if (sid === sessionId) return;
        setSessionId(sid);
        setMessages([]); // Clear messages temporarily while loading
        setDocumentUploaded(false);
    };

    const handleDeleteSession = async (sid, e) => {
        e.stopPropagation();
        setSessionToDelete(sid);
        setDeleteDialogOpen(true);
    };

    const confirmDeleteSession = async () => {
        if (!sessionToDelete) return;
        
        try {
            const response = await fetch(`${API_BASE_URL}/sessions/${sessionToDelete}`, {
                method: 'DELETE'
            });
            if (!response.ok) throw new Error('Failed to delete session');
            
            // If deleted session is current, switch to another or create new
            if (sessionToDelete === sessionId) {
                const remainingSessions = sessions.filter(s => s.session_id !== sessionToDelete);
                if (remainingSessions.length > 0) {
                    setSessionId(remainingSessions[0].session_id);
                } else {
                    await createNewSession();
                }
            }
            
            // Reload sessions
            await loadSessions();
        } catch (error) {
            console.error('Error deleting session:', error);
            alert('Failed to delete session');
        } finally {
            setDeleteDialogOpen(false);
            setSessionToDelete(null);
        }
    };

    const handleFileChange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        setIsUploading(true);
        setFileName(file.name);
        setMessages([{ text: `Uploading and processing "${file.name}"... This may take a moment.`, sender: 'ai' }]);
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', sessionId);
        
        try {
            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "File processing failed.");
            }
            
            setDocumentUploaded(true);
            setMessages([{ text: `Processing complete! You can now ask questions about "${file.name}".`, sender: 'ai' }]);
            
            // Reload sessions to update title
            await loadSessions();
        } catch (error) {
            setMessages([{ text: `Sorry, the file could not be processed. Error: ${error.message}`, sender: 'ai' }]);
        } finally {
            setIsUploading(false);
        }
    };

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim() || isLoading || !sessionId) return;
        
        const userMessage = { text: input, sender: "user" };
        setMessages(prev => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);
        
        try {
            const response = await fetch(`${API_BASE_URL}/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userMessage.text, session_id: sessionId })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `API error`);
            }
            
            const data = await response.json();
            const formatApiResponse = (apiResponse) => {
                let formattedText = `**${apiResponse.problem_summary}**\n\n`;
                
                if (apiResponse.possible_causes?.length > 0) {
                    formattedText += "**Possible Causes:**\n";
                    apiResponse.possible_causes.forEach((cause, idx) => {
                        formattedText += `${idx + 1}. ${cause}\n`;
                    });
                    formattedText += "\n";
                }
                
                if (apiResponse.remediation_steps?.length > 0) {
                    formattedText += "**Recommended Steps:**\n";
                    apiResponse.remediation_steps.forEach(step => {
                        formattedText += `${step.step}. ${step.action}\n`;
                    });
                    formattedText += "\n";
                }
                
                if (apiResponse.evidence?.length > 0) {
                    formattedText += "**Evidence:**\n";
                    apiResponse.evidence.forEach((ev, idx) => {
                        formattedText += `${idx + 1}. ${ev.quote} (Page ${ev.page})\n`;
                    });
                    formattedText += "\n";
                }
                
                if (apiResponse.references?.length > 0) {
                    formattedText += "**References:**\n";
                    apiResponse.references.forEach((ref, idx) => {
                        formattedText += `${idx + 1}. ${ref.figure || 'Reference'} - Page ${ref.page}\n`;
                    });
                    formattedText += "\n";
                }
                
                if (apiResponse.safety_summary) {
                    formattedText += `**Safety Note:** ${apiResponse.safety_summary}\n`;
                }
                
                return formattedText;
            };
            
            const aiMessage = { text: formatApiResponse(data), sender: "ai" };
            setMessages(prev => [...prev, aiMessage]);
            
            // Reload sessions to update last message preview
            await loadSessions();
        } catch (error) {
            const errorMessage = { text: `An error occurred: ${error.message}`, sender: "ai" };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const renderUploadView = () => {
        return (
            <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" height="100%">
                <Typography variant="h5" gutterBottom>Upload Document to Begin</Typography>
                <Typography color="text.secondary" sx={{ mb: 3 }}>
                    Please upload a PDF manual to start your session.
                </Typography>
                <Button 
                    variant="contained" 
                    component="label" 
                    startIcon={<UploadFileIcon />} 
                    disabled={isUploading}
                >
                    {isUploading ? 'Processing...' : 'Choose PDF File'}
                    <input type="file" hidden onChange={handleFileChange} accept=".pdf" />
                </Button>
                {isUploading && <CircularProgress sx={{ mt: 2 }} />}
            </Box>
        );
    };

    const renderChatView = () => (
        <Box display="flex" flexDirection="column" height="100%">
            <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 2 }}>
                {messages.map((msg, index) => (
                    <Paper key={index} elevation={3} className={`message ${msg.sender}`}>
                        <ReactMarkdown>{msg.text}</ReactMarkdown>
                    </Paper>
                ))}
                {isLoading && (
                    <Paper elevation={3} className="message ai">
                        <TypingIndicator />
                    </Paper>
                )}
                <div ref={chatEndRef} />
            </Box>
            <Box component="form" onSubmit={handleSendMessage} sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
                <TextField 
                    fullWidth 
                    variant="outlined" 
                    placeholder="Ask a question..." 
                    value={input} 
                    onChange={(e) => setInput(e.target.value)} 
                    disabled={isLoading}
                    InputProps={{
                        endAdornment: (
                            <IconButton type="submit" color="primary" disabled={isLoading}>
                                <SendIcon />
                            </IconButton>
                        ),
                    }} 
                />
            </Box>
        </Box>
    );

    return (
        <Box sx={{ display: 'flex', height: '100vh' }}>
            {/* Sidebar */}
            <Drawer
                variant="persistent"
                open={sidebarOpen}
                sx={{
                    width: drawerWidth,
                    flexShrink: 0,
                    '& .MuiDrawer-paper': {
                        width: drawerWidth,
                        boxSizing: 'border-box',
                        borderRight: '1px solid rgba(0, 0, 0, 0.12)'
                    },
                }}
            >
                <Toolbar sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="h6" noWrap component="div">
                        Chat History
                    </Typography>
                    <IconButton onClick={() => setSidebarOpen(false)}>
                        <MenuIcon />
                    </IconButton>
                </Toolbar>
                <Divider />
                <Box sx={{ p: 1 }}>
                    <Button
                        fullWidth
                        variant="contained"
                        startIcon={<AddIcon />}
                        onClick={createNewSession}
                        sx={{ mb: 1 }}
                    >
                        New Chat
                    </Button>
                </Box>
                <Divider />
                <List sx={{ overflow: 'auto', flexGrow: 1 }}>
                    {loadingSessions ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                            <CircularProgress size={24} />
                        </Box>
                    ) : sessions.length === 0 ? (
                        <ListItem>
                            <ListItemText 
                                primary="No chats yet" 
                                secondary="Create a new chat to get started"
                            />
                        </ListItem>
                    ) : (
                        sessions.map((session) => (
                            <ListItem
                                key={session.session_id}
                                disablePadding
                                secondaryAction={
                                    <IconButton
                                        edge="end"
                                        onClick={(e) => handleDeleteSession(session.session_id, e)}
                                        size="small"
                                    >
                                        <DeleteIcon fontSize="small" />
                                    </IconButton>
                                }
                            >
                                <ListItemButton
                                    selected={session.session_id === sessionId}
                                    onClick={() => switchSession(session.session_id)}
                                    sx={{
                                        '&.Mui-selected': {
                                            backgroundColor: 'rgba(25, 118, 210, 0.08)',
                                            '&:hover': {
                                                backgroundColor: 'rgba(25, 118, 210, 0.12)',
                                            },
                                        },
                                    }}
                                >
                                    <ListItemText
                                        primary={session.title}
                                        secondary={
                                            <Box>
                                                <Typography variant="caption" display="block">
                                                    {formatDate(session.updated_at)}
                                                </Typography>
                                                <Typography 
                                                    variant="caption" 
                                                    color="text.secondary"
                                                    sx={{ 
                                                        display: 'block',
                                                        overflow: 'hidden',
                                                        textOverflow: 'ellipsis',
                                                        whiteSpace: 'nowrap'
                                                    }}
                                                >
                                                    {session.last_message_preview}
                                                </Typography>
                                            </Box>
                                        }
                                    />
                                </ListItemButton>
                            </ListItem>
                        ))
                    )}
                </List>
            </Drawer>

            {/* Main Content */}
            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    width: { sm: `calc(100% - ${drawerWidth}px)` },
                    display: 'flex',
                    flexDirection: 'column',
                    height: '100vh'
                }}
            >
                {!sidebarOpen && (
                    <IconButton
                        onClick={() => setSidebarOpen(true)}
                        sx={{ position: 'absolute', top: 16, left: 16, zIndex: 1300 }}
                    >
                        <MenuIcon />
                    </IconButton>
                )}
                
                <Paper elevation={4} sx={{ p: 2, textAlign: 'center', borderRadius: 0 }}>
                    <Typography variant="h5" component="h1">MarineMind AI</Typography>
                    {documentUploaded && (
                        <Typography color="text.secondary">
                            Chatting about: <strong>{fileName}</strong>
                        </Typography>
                    )}
                </Paper>
                
                <Box sx={{ flexGrow: 1, height: '100%', overflow: 'hidden' }}>
                    {documentUploaded ? renderChatView() : renderUploadView()}
                </Box>
            </Box>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
                <DialogTitle>Delete Chat?</DialogTitle>
                <DialogContent>
                    <Typography>
                        Are you sure you want to delete this chat? This action cannot be undone.
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
                    <Button onClick={confirmDeleteSession} color="error" variant="contained">
                        Delete
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}

export default RagChat;
