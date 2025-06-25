import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Layout from '@/components/Layout';
import DrawingUpload from '@/components/DrawingUpload';
import DrawingList from '@/components/DrawingList';
import EnhancedAnalysis from '@/components/EnhancedAnalysis';
import TaskMonitorDemo from '@/pages/task-monitor';

const theme = createTheme();

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/upload" replace />} />
            <Route path="/upload" element={<DrawingUpload />} />
            <Route path="/list" element={<DrawingList />} />
            <Route path="/enhanced" element={<EnhancedAnalysis />} />
            <Route path="/task-monitor" element={<TaskMonitorDemo />} />
          </Routes>
        </Layout>
      </Router>
    </ThemeProvider>
  );
}

export default App; 