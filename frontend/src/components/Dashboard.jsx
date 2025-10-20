// File: frontend/src/components/Dashboard.jsx

import React from 'react';
import { Link } from 'react-router-dom';
import { Container, Typography, Grid, Card, CardActionArea, CardContent, Box } from '@mui/material';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import SpeedIcon from '@mui/icons-material/Speed';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import { motion } from 'framer-motion';

const features = [
    { title: 'Machinery Issues', description: 'Upload a manual and ask questions to troubleshoot machinery problems.', link: '/rag-chat', icon: <PrecisionManufacturingIcon sx={{ fontSize: 40 }} />, disabled: false },
    { title: 'Vessel Performance Overview', description: 'Analyze noon reports to track vessel efficiency.', link: '#', icon: <SpeedIcon sx={{ fontSize: 40 }} />, disabled: true },
    { title: 'Noon Report Anomaly Detection', description: 'Automatically detect anomalies in noon report data.', link: '#', icon: <ReportProblemIcon sx={{ fontSize: 40 }} />, disabled: true },
];


function Dashboard() {
  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Box sx={{ textAlign: 'center', mb: 6 }}>
         {/* ... (Typography remains the same) ... */}
         <Typography variant="h3" component="h1" gutterBottom>MarineMind AI</Typography>
         <Typography variant="h6" color="text.secondary">Your AI Assistant for Marine Operations</Typography>

      </Box>

      <Grid container spacing={4}>
        {features.map((feature, index) => (
          <Grid item xs={12} md={4} key={index}>
            {/* --- WRAP CARD WITH MOTION.DIV FOR ANIMATION --- */}
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              style={{ height: '100%' }}
            >
              <Card 
                component={feature.disabled ? 'div' : Link} 
                to={feature.link} 
                sx={{ 
                  textDecoration: 'none',
                  opacity: feature.disabled ? 0.5 : 1,
                  cursor: feature.disabled ? 'not-allowed' : 'pointer',
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column'
                }}
              >
                {/* ... (CardActionArea and CardContent remain the same) ... */}
                <CardActionArea disabled={feature.disabled} sx={{ flexGrow: 1 }}>
                    <CardContent sx={{ textAlign: 'center' }}>
                        <Box sx={{ mb: 2, color: 'primary.main' }}>{feature.icon}</Box>
                        <Typography gutterBottom variant="h5" component="div">{feature.title}</Typography>
                        <Typography variant="body2" color="text.secondary">{feature.description}</Typography>
                    </CardContent>
                </CardActionArea>
              </Card>
            </motion.div>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}

export default Dashboard;