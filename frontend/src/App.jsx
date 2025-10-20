import React, { useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';
import Particles from "react-tsparticles";
import { loadSlim } from "tsparticles-slim"; 

import Dashboard from './components/Dashboard';
import RagChat from './pages/RagChat';
import { particleOptions } from './particlesConfig';

function App() {
 
  const particlesInit = useCallback(async engine => {

    await loadSlim(engine);
  }, []);

  return (
    <Router>
      {/* We pass our init function to the component's `init` prop. */}
      {/* The component will handle the loading state internally. */}
      <Particles
        id="tsparticles"
        init={particlesInit}
        options={particleOptions}
      />
      
      <Box
        sx={{
          position: 'relative',
          zIndex: 1,
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/rag-chat" element={<RagChat />} />
        </Routes>
      </Box>
    </Router>
  );
}

export default App;