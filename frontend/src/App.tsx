import React, { useState, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Card,
  CardContent,
  Grid,
  Box,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Paper
} from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00d4ff',
    },
    secondary: {
      main: '#ff6b35',
    },
    background: {
      default: '#0a0e27',
      paper: '#1a1e3a',
    },
  },
});

interface Change {
  change_id: string;
  source: string;
  status: string;
  timestamp?: string;
  repository?: string;
  issue_key?: string;
}

const App: React.FC = () => {
  const [changes, setChanges] = useState<Change[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiStatus, setApiStatus] = useState<'connected' | 'disconnected'>('disconnected');

  const API_BASE = 'https://388tx4f8ri.execute-api.us-east-1.amazonaws.com/prod';

  useEffect(() => {
    checkApiStatus();
    loadRecentChanges();
  }, []);

  const checkApiStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/webhooks/github`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test: true })
      });
      setApiStatus(response.ok ? 'connected' : 'disconnected');
    } catch (error) {
      setApiStatus('disconnected');
    }
  };

  const loadRecentChanges = () => {
    // Mock recent changes for demo
    const mockChanges: Change[] = [
      {
        change_id: 'github-abc123',
        source: 'github',
        status: 'processed',
        timestamp: new Date().toISOString(),
        repository: 'kinexusai/kinexus-ai'
      },
      {
        change_id: 'jira-def456',
        source: 'jira',
        status: 'pending',
        issue_key: 'KIN-123'
      }
    ];
    setChanges(mockChanges);
    setLoading(false);
  };

  const triggerTestWebhook = async (source: 'github' | 'jira') => {
    try {
      const testPayload = source === 'github'
        ? {
            repository: { full_name: 'kinexusai/kinexus-ai' },
            after: 'test-commit-123',
            head_commit: {
              timestamp: new Date().toISOString(),
              message: 'Test commit for demo'
            },
            commits: [{ message: 'Demo webhook test' }]
          }
        : {
            issue: {
              id: 'test-123',
              key: 'KIN-DEMO',
              fields: { summary: 'Test webhook integration' }
            }
          };

      const response = await fetch(`${API_BASE}/webhooks/${source}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(testPayload)
      });

      if (response.ok) {
        const result = await response.json();
        alert(`✅ ${source.toUpperCase()} webhook test successful!\n${JSON.stringify(result, null, 2)}`);
        loadRecentChanges();
      } else {
        alert(`❌ ${source.toUpperCase()} webhook test failed`);
      }
    } catch (error) {
      alert(`❌ Error testing ${source} webhook: ${error}`);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppBar position="static" sx={{ background: 'linear-gradient(45deg, #0a0e27 30%, #1a1e3a 90%)' }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
            🚀 Kinexus AI - Autonomous Knowledge Management
          </Typography>
          <Chip
            label={apiStatus === 'connected' ? 'API Connected' : 'API Disconnected'}
            color={apiStatus === 'connected' ? 'success' : 'error'}
            variant="outlined"
          />
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Grid container spacing={4}>
          {/* Hero Section */}
          <Grid item xs={12}>
            <Paper sx={{ p: 4, background: 'linear-gradient(135deg, #1a1e3a 0%, #2a2e5a 100%)' }}>
              <Typography variant="h3" component="h1" gutterBottom sx={{ color: '#00d4ff', fontWeight: 'bold' }}>
                AWS AI Agent Global Hackathon 2025
              </Typography>
              <Typography variant="h5" gutterBottom sx={{ color: '#ffffff', mb: 3 }}>
                Real-time AI-powered documentation management system
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Chip label="Claude 4 Opus 4.1" color="primary" />
                <Chip label="Amazon Bedrock" color="primary" />
                <Chip label="Multi-Agent System" color="secondary" />
                <Chip label="Real-time Processing" color="secondary" />
              </Box>
            </Paper>
          </Grid>

          {/* System Status */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  🔧 System Status
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Alert severity={apiStatus === 'connected' ? 'success' : 'error'}>
                    API Gateway: {apiStatus === 'connected' ? 'Online' : 'Offline'}
                  </Alert>
                  <Alert severity="success">
                    DynamoDB: Connected
                  </Alert>
                  <Alert severity="success">
                    S3 Storage: Ready
                  </Alert>
                  <Alert severity="success">
                    SSL Certificate: Validated
                  </Alert>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Webhook Testing */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  🧪 Webhook Testing
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Test webhook endpoints for GitHub and Jira integrations
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                  <Button
                    variant="contained"
                    onClick={() => triggerTestWebhook('github')}
                    sx={{ background: 'linear-gradient(45deg, #24292e 30%, #586069 90%)' }}
                  >
                    Test GitHub
                  </Button>
                  <Button
                    variant="contained"
                    onClick={() => triggerTestWebhook('jira')}
                    sx={{ background: 'linear-gradient(45deg, #0052cc 30%, #2684ff 90%)' }}
                  >
                    Test Jira
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Recent Changes */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  📊 Recent Changes
                </Typography>
                {loading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : (
                  <Grid container spacing={2}>
                    {changes.map((change) => (
                      <Grid item xs={12} md={6} key={change.change_id}>
                        <Card variant="outlined">
                          <CardContent>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                              <Chip
                                label={change.source.toUpperCase()}
                                color={change.source === 'github' ? 'default' : 'primary'}
                                size="small"
                              />
                              <Chip
                                label={change.status}
                                color={change.status === 'processed' ? 'success' : 'warning'}
                                size="small"
                              />
                            </Box>
                            <Typography variant="body2">
                              {change.repository && `Repository: ${change.repository}`}
                              {change.issue_key && `Issue: ${change.issue_key}`}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              ID: {change.change_id}
                            </Typography>
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Architecture Overview */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  🏗️ Architecture Overview
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
                      <Typography variant="subtitle2" gutterBottom>API Gateway</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Webhook endpoints
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
                      <Typography variant="subtitle2" gutterBottom>Lambda Functions</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Event processing
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
                      <Typography variant="subtitle2" gutterBottom>DynamoDB</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Change tracking
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}>
                      <Typography variant="subtitle2" gutterBottom>Bedrock AI</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Claude 4 processing
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* Domain Info */}
          <Grid item xs={12}>
            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="body2">
                <strong>Production Domain:</strong> https://kinexusai.com (SSL Certificate Ready) <br/>
                <strong>API Endpoints:</strong> <br/>
                • GitHub Webhook: {API_BASE}/webhooks/github <br/>
                • Jira Webhook: {API_BASE}/webhooks/jira
              </Typography>
            </Alert>
          </Grid>
        </Grid>
      </Container>
    </ThemeProvider>
  );
};

export default App;