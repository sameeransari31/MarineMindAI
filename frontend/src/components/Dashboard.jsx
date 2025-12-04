// File: frontend/src/components/Dashboard.jsx

import React from 'react';
import { Link } from 'react-router-dom';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardActionArea,
  CardContent,
  Box,
  Chip,
} from '@mui/material';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import SpeedIcon from '@mui/icons-material/Speed';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import { motion } from 'framer-motion';

const features = [
  {
    title: 'Machinery Issues Assistant',
    description: 'Upload a technical manual and chat with MarineMind to troubleshoot machinery issues in real time.',
    link: '/rag-chat',
    icon: <PrecisionManufacturingIcon sx={{ fontSize: 40 }} />,
    disabled: false,
    tag: 'Available now',
  },
  {
    title: 'Vessel Performance Overview',
    description: 'Analyze noon reports to track fuel consumption and overall vessel efficiency.',
    link: '#',
    icon: <SpeedIcon sx={{ fontSize: 40 }} />,
    disabled: true,
    tag: 'Coming soon',
  },
  {
    title: 'Noon Report Anomaly Detection',
    description: 'Automatically detect anomalies in noon report data before they become major issues.',
    link: '#',
    icon: <ReportProblemIcon sx={{ fontSize: 40 }} />,
    disabled: true,
    tag: 'In design',
  },
];

function Dashboard() {
  return (
    <Container
      maxWidth="lg"
      sx={{
        py: 10,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <Box sx={{ textAlign: 'center' }}>
        <Typography
          variant="overline"
          sx={{
            letterSpacing: 4,
            color: 'secondary.main',
          }}
        >
          MARINE OPERATIONS COPILOT
        </Typography>
        <Typography
          variant="h3"
          component="h1"
          gutterBottom
          sx={{
            mt: 1,
            fontWeight: 700,
          }}
        >
          MarineMind AI
        </Typography>
        <Typography
          variant="h6"
          color="text.secondary"
          sx={{
            maxWidth: 720,
            mx: 'auto',
          }}
        >
          A focused AI assistant designed to work with marine manuals and reports, helping you
          diagnose issues faster and make safer operational decisions.
        </Typography>
      </Box>

      <Grid container spacing={4}>
        {features.map((feature, index) => (
          <Grid item xs={12} md={4} key={feature.title}>
            <motion.div
              initial={{ opacity: 0, y: 32 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              style={{ height: '100%' }}
            >
              <Card
                variant="glass"
                component={feature.disabled ? 'div' : Link}
                to={feature.link}
                sx={{
                  textDecoration: 'none',
                  opacity: feature.disabled ? 0.5 : 1,
                  cursor: feature.disabled ? 'not-allowed' : 'pointer',
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  borderRadius: 3,
                  overflow: 'hidden',
                  '&:hover': !feature.disabled
                    ? {
                        transform: 'translateY(-4px)',
                        boxShadow: 10,
                      }
                    : undefined,
                  transition: 'all 0.25s ease-out',
                }}
              >
                <CardActionArea disabled={feature.disabled} sx={{ flexGrow: 1, p: 1.5 }}>
                  <CardContent
                    sx={{
                      textAlign: 'left',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 2,
                    }}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <Box
                        sx={{
                          mb: 1,
                          color: 'primary.main',
                        }}
                      >
                        {feature.icon}
                      </Box>
                      <Chip
                        label={feature.tag}
                        size="small"
                        color={feature.disabled ? 'default' : 'secondary'}
                        variant={feature.disabled ? 'outlined' : 'filled'}
                      />
                    </Box>
                    <Typography gutterBottom variant="h5" component="div">
                      {feature.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {feature.description}
                    </Typography>
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