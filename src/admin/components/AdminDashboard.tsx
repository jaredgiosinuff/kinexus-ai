import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  AppBar,
  Toolbar,
  Tab,
  Tabs,
  Badge,
  Alert,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Switch,
  FormControlLabel,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Settings as SettingsIcon,
  Security as SecurityIcon,
  Chat as ChatIcon,
  Integration as IntegrationIcon,
  Visibility as VisibilityIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CloudUpload as CloudUploadIcon,
  Computer as ComputerIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  SmartToy as SmartToyIcon,
  Psychology as PsychologyIcon,
  Speed as SpeedIcon,
  AttachMoney as AttachMoneyIcon
} from '@mui/icons-material';
import { Line, Pie, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  ArcElement,
  BarElement
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  ChartTooltip,
  Legend,
  ArcElement,
  BarElement
);

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

interface SystemMetrics {
  activeAgents: number;
  reasoningChains: number;
  requestRate: number;
  errorRate: number;
  responseTime: number;
  totalCost: number;
  tokensProcessed: number;
}

interface AgentConversation {
  id: string;
  agentType: string;
  task: string;
  status: 'running' | 'completed' | 'failed';
  startTime: string;
  duration?: number;
  thoughts: number;
  confidence: number;
  modelUsed: string;
  cost: number;
}

interface Integration {
  id: string;
  name: string;
  type: 'source' | 'target' | 'both';
  status: 'active' | 'inactive' | 'error';
  lastSync: string;
  config: Record<string, any>;
}

interface AuthProvider {
  type: 'cognito' | 'local';
  enabled: boolean;
  config: Record<string, any>;
}

export const AdminDashboard: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics>({
    activeAgents: 0,
    reasoningChains: 0,
    requestRate: 0,
    errorRate: 0,
    responseTime: 0,
    totalCost: 0,
    tokensProcessed: 0
  });
  const [conversations, setConversations] = useState<AgentConversation[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [authProvider, setAuthProvider] = useState<AuthProvider>({
    type: 'local',
    enabled: true,
    config: {}
  });
  const [loading, setLoading] = useState(true);
  const [configDialog, setConfigDialog] = useState<{
    open: boolean;
    type: 'auth' | 'integration';
    data?: any;
  }>({ open: false, type: 'auth' });

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      // Load system metrics
      const metricsResponse = await fetch('/api/admin/metrics');
      const metrics = await metricsResponse.json();
      setSystemMetrics(metrics);

      // Load agent conversations
      const conversationsResponse = await fetch('/api/admin/conversations');
      const conversationsData = await conversationsResponse.json();
      setConversations(conversationsData);

      // Load integrations
      const integrationsResponse = await fetch('/api/admin/integrations');
      const integrationsData = await integrationsResponse.json();
      setIntegrations(integrationsData);

      // Load auth config
      const authResponse = await fetch('/api/admin/auth/config');
      const authData = await authResponse.json();
      setAuthProvider(authData);

    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const renderOverviewTab = () => {
    const agentPerformanceData = {
      labels: ['Last 24h', 'Last 12h', 'Last 6h', 'Last 3h', 'Last 1h'],
      datasets: [
        {
          label: 'Reasoning Chains',
          data: [145, 89, 56, 34, 12],
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
        },
        {
          label: 'Average Confidence',
          data: [0.87, 0.89, 0.91, 0.88, 0.92],
          borderColor: 'rgb(255, 99, 132)',
          backgroundColor: 'rgba(255, 99, 132, 0.2)',
        }
      ]
    };

    const modelUsageData = {
      labels: ['Claude 4 Opus', 'Claude 4 Sonnet', 'Nova Pro', 'Nova Lite', 'GPT-4 Turbo'],
      datasets: [{
        data: [35, 25, 20, 15, 5],
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF'
        ]
      }]
    };

    return (
      <Grid container spacing={3}>
        {/* Key Metrics Cards */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <SmartToyIcon color="primary" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Active Agents
                  </Typography>
                  <Typography variant="h4">
                    {systemMetrics.activeAgents}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <PsychologyIcon color="secondary" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Reasoning Chains
                  </Typography>
                  <Typography variant="h4">
                    {systemMetrics.reasoningChains}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <SpeedIcon color="info" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Avg Response Time
                  </Typography>
                  <Typography variant="h4">
                    {systemMetrics.responseTime}ms
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <AttachMoneyIcon color="warning" sx={{ mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Cost (24h)
                  </Typography>
                  <Typography variant="h4">
                    ${systemMetrics.totalCost.toFixed(2)}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Charts */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Agent Performance Trends
              </Typography>
              <Line data={agentPerformanceData} options={{
                responsive: true,
                scales: {
                  y: {
                    beginAtZero: true
                  }
                }
              }} />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Model Usage Distribution
              </Typography>
              <Pie data={modelUsageData} options={{ responsive: true }} />
            </CardContent>
          </Card>
        </Grid>

        {/* System Health */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Health
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={3}>
                  <Box display="flex" alignItems="center">
                    <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                    <Typography>API Gateway: Healthy</Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Box display="flex" alignItems="center">
                    <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                    <Typography>Database: Healthy</Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Box display="flex" alignItems="center">
                    <WarningIcon color="warning" sx={{ mr: 1 }} />
                    <Typography>Redis: Degraded</Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Box display="flex" alignItems="center">
                    <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                    <Typography>Bedrock: Healthy</Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  const renderConversationsTab = () => {
    return (
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  Active Agent Conversations
                </Typography>
                <Button
                  startIcon={<RefreshIcon />}
                  onClick={loadDashboardData}
                  disabled={loading}
                >
                  Refresh
                </Button>
              </Box>

              {loading && <LinearProgress />}

              <List>
                {conversations.map((conversation) => (
                  <ListItem key={conversation.id} divider>
                    <ListItemIcon>
                      <SmartToyIcon color={
                        conversation.status === 'running' ? 'primary' :
                        conversation.status === 'completed' ? 'success' : 'error'
                      } />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="subtitle1">
                            {conversation.agentType}
                          </Typography>
                          <Chip
                            label={conversation.status}
                            size="small"
                            color={
                              conversation.status === 'running' ? 'primary' :
                              conversation.status === 'completed' ? 'success' : 'error'
                            }
                          />
                          <Chip
                            label={`${conversation.thoughts} thoughts`}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`${(conversation.confidence * 100).toFixed(1)}% confidence`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="textSecondary">
                            Task: {conversation.task}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            Model: {conversation.modelUsed} | Cost: ${conversation.cost.toFixed(4)} | Started: {new Date(conversation.startTime).toLocaleString()}
                          </Typography>
                        </Box>
                      }
                    />
                    <IconButton edge="end">
                      <VisibilityIcon />
                    </IconButton>
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  const renderAuthTab = () => {
    const handleAuthProviderChange = (newType: 'cognito' | 'local') => {
      setAuthProvider(prev => ({ ...prev, type: newType }));
    };

    const handleSaveAuthConfig = async () => {
      try {
        await fetch('/api/admin/auth/config', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(authProvider)
        });
        // Show success message
      } catch (error) {
        console.error('Failed to save auth config:', error);
      }
    };

    return (
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Authentication Provider
              </Typography>

              <Box mb={3}>
                <FormControl fullWidth>
                  <InputLabel>Authentication Type</InputLabel>
                  <Select
                    value={authProvider.type}
                    onChange={(e) => handleAuthProviderChange(e.target.value as 'cognito' | 'local')}
                  >
                    <MenuItem value="local">
                      <Box display="flex" alignItems="center">
                        <ComputerIcon sx={{ mr: 1 }} />
                        Local Authentication
                      </Box>
                    </MenuItem>
                    <MenuItem value="cognito">
                      <Box display="flex" alignItems="center">
                        <CloudUploadIcon sx={{ mr: 1 }} />
                        AWS Cognito
                      </Box>
                    </MenuItem>
                  </Select>
                </FormControl>
              </Box>

              {authProvider.type === 'cognito' && (
                <Box>
                  <TextField
                    fullWidth
                    label="User Pool ID"
                    margin="normal"
                    value={authProvider.config.userPoolId || ''}
                    onChange={(e) => setAuthProvider(prev => ({
                      ...prev,
                      config: { ...prev.config, userPoolId: e.target.value }
                    }))}
                  />
                  <TextField
                    fullWidth
                    label="Client ID"
                    margin="normal"
                    value={authProvider.config.clientId || ''}
                    onChange={(e) => setAuthProvider(prev => ({
                      ...prev,
                      config: { ...prev.config, clientId: e.target.value }
                    }))}
                  />
                  <TextField
                    fullWidth
                    label="Region"
                    margin="normal"
                    value={authProvider.config.region || 'us-east-1'}
                    onChange={(e) => setAuthProvider(prev => ({
                      ...prev,
                      config: { ...prev.config, region: e.target.value }
                    }))}
                  />
                </Box>
              )}

              <Box mt={3}>
                <Button
                  variant="contained"
                  onClick={handleSaveAuthConfig}
                  fullWidth
                >
                  Save Configuration
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Authentication Status
              </Typography>

              <Box display="flex" alignItems="center" mb={2}>
                {authProvider.enabled ? (
                  <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                ) : (
                  <ErrorIcon color="error" sx={{ mr: 1 }} />
                )}
                <Typography>
                  {authProvider.enabled ? 'Authentication Enabled' : 'Authentication Disabled'}
                </Typography>
              </Box>

              <Typography variant="body2" color="textSecondary" paragraph>
                Current provider: {authProvider.type === 'cognito' ? 'AWS Cognito' : 'Local Authentication'}
              </Typography>

              {authProvider.type === 'cognito' && (
                <Alert severity="info">
                  Cognito integration provides enterprise-grade authentication with
                  multi-factor authentication, user management, and integration with
                  AWS Identity Center.
                </Alert>
              )}

              {authProvider.type === 'local' && (
                <Alert severity="warning">
                  Local authentication is suitable for development and small deployments.
                  Consider AWS Cognito for production environments.
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  const renderIntegrationsTab = () => {
    const handleToggleIntegration = async (integrationId: string, enabled: boolean) => {
      try {
        await fetch(`/api/admin/integrations/${integrationId}/toggle`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled })
        });
        loadDashboardData();
      } catch (error) {
        console.error('Failed to toggle integration:', error);
      }
    };

    return (
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  Knowledge Source Integrations
                </Typography>
                <Button
                  startIcon={<AddIcon />}
                  variant="contained"
                  onClick={() => setConfigDialog({ open: true, type: 'integration' })}
                >
                  Add Integration
                </Button>
              </Box>

              <Grid container spacing={2}>
                {integrations.map((integration) => (
                  <Grid item xs={12} md={6} lg={4} key={integration.id}>
                    <Card variant="outlined">
                      <CardContent>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                          <Typography variant="h6">
                            {integration.name}
                          </Typography>
                          <Chip
                            label={integration.status}
                            size="small"
                            color={
                              integration.status === 'active' ? 'success' :
                              integration.status === 'inactive' ? 'default' : 'error'
                            }
                          />
                        </Box>

                        <Typography variant="body2" color="textSecondary" gutterBottom>
                          Type: {integration.type}
                        </Typography>

                        <Typography variant="caption" color="textSecondary">
                          Last sync: {new Date(integration.lastSync).toLocaleString()}
                        </Typography>

                        <Box mt={2} display="flex" justifyContent="space-between">
                          <FormControlLabel
                            control={
                              <Switch
                                checked={integration.status === 'active'}
                                onChange={(e) => handleToggleIntegration(integration.id, e.target.checked)}
                              />
                            }
                            label="Enabled"
                          />
                          <Box>
                            <IconButton size="small">
                              <EditIcon />
                            </IconButton>
                            <IconButton size="small" color="error">
                              <DeleteIcon />
                            </IconButton>
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Kinexus AI - Admin Dashboard
          </Typography>
          <Chip
            icon={authProvider.type === 'cognito' ? <CloudUploadIcon /> : <ComputerIcon />}
            label={authProvider.type === 'cognito' ? 'AWS Cognito' : 'Local Auth'}
            color="secondary"
            variant="outlined"
          />
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 3 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab
              icon={<DashboardIcon />}
              label="Overview"
              iconPosition="start"
            />
            <Tab
              icon={<Badge badgeContent={conversations.filter(c => c.status === 'running').length} color="primary">
                <ChatIcon />
              </Badge>}
              label="Conversations"
              iconPosition="start"
            />
            <Tab
              icon={<SecurityIcon />}
              label="Authentication"
              iconPosition="start"
            />
            <Tab
              icon={<IntegrationIcon />}
              label="Integrations"
              iconPosition="start"
            />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          {renderOverviewTab()}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {renderConversationsTab()}
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {renderAuthTab()}
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          {renderIntegrationsTab()}
        </TabPanel>
      </Container>

      {/* Configuration Dialog */}
      <Dialog
        open={configDialog.open}
        onClose={() => setConfigDialog({ open: false, type: 'auth' })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {configDialog.type === 'auth' ? 'Authentication Configuration' : 'Add Integration'}
        </DialogTitle>
        <DialogContent>
          {/* Dialog content would be implemented based on type */}
          <Typography>Configuration form would go here...</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigDialog({ open: false, type: 'auth' })}>
            Cancel
          </Button>
          <Button variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};