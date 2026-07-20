import React, { useEffect, useState } from "react";
import {
  Card,
  Col,
  Row,
  Input,
  Button,
  Badge,
  Spin,
  Alert,
  Typography,
  Space,
  notification,
  theme
} from "antd";
import {
  KeyOutlined,
  LinkOutlined,
  ApiOutlined,
  SaveOutlined,
  ExperimentOutlined,
  SyncOutlined,
  CloudDownloadOutlined,
  EyeInvisibleOutlined,
  EyeTwoTone
} from "@ant-design/icons";
import { API_URL, TOKEN_KEY } from "../../providers/constants";

const { Title, Text, Paragraph } = Typography;

interface Integration {
  id: string;
  name: string;
  connected: boolean;
  apiKey: string;
  webhookUrl: string | null;
  config: any;
  lastSyncedAt?: string | null;
}

const PROVIDER_INFO: Record<string, { desc: string; color: string; webhookDesc: string }> = {
  vapi: {
    desc: "Benten automatically ingests call recordings, transcripts, and telemetry via Vapi's webhook payloads.",
    color: "#8b5cf6",
    webhookDesc: "Set this URL in your Vapi Dashboard under Webhooks to auto-evaluate calls."
  },
  retell: {
    desc: "Fetch agent responses, latency logs, and conversation transcripts from your Retell AI account.",
    color: "#10b981",
    webhookDesc: "Configure this webhook URL inside your Retell developer settings."
  },
  elevenlabs: {
    desc: "Ingest custom agent profiles, speech synthesis, and voice performance parameters from ElevenLabs.",
    color: "#f59e0b",
    webhookDesc: "Provide this Webhook endpoint inside ElevenLabs developer settings."
  }
};

export const IntegrationsPage: React.FC = () => {
  const { token } = theme.useToken();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Separate states for inputs so users can edit them
  const [formStates, setFormStates] = useState<Record<string, { apiKey: string; webhookUrl: string }>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [syncingCallsId, setSyncingCallsId] = useState<string | null>(null);
  const [syncingAgentsId, setSyncingAgentsId] = useState<string | null>(null);

  // Track connection test result alerts
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});

  const fetchIntegrations = async () => {
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const response = await fetch(`${API_URL}/integrations`, {
        headers: {
          Authorization: `Bearer ${tokenVal}`
        }
      });

      if (!response.ok) {
        throw new Error("Failed to fetch integrations");
      }

      const data = await response.json();
      const filtered = data.filter((item: Integration) => item.id !== "openai");
      setIntegrations(filtered);
      
      const states: Record<string, { apiKey: string; webhookUrl: string }> = {};
      filtered.forEach((item: Integration) => {
        states[item.id] = {
          apiKey: item.apiKey || "",
          webhookUrl: item.webhookUrl || ""
        };
      });
      setFormStates(states);
      setError(null);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load integrations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleInputChange = (id: string, field: "apiKey" | "webhookUrl", value: string) => {
    setFormStates(prev => ({
      ...prev,
      [id]: {
        ...prev[id],
        [field]: value
      }
    }));
    
    if (field === "apiKey") {
      setTestResults(prev => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    }
  };

  const handleTestConnection = async (id: string) => {
    setTestingId(id);
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const apiKey = formStates[id]?.apiKey || "";

      const response = await fetch(`${API_URL}/integrations/${id}/test`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tokenVal}`
        },
        body: JSON.stringify({ apiKey })
      });

      if (!response.ok) {
        throw new Error("Connection test request failed");
      }

      const resData = await response.json();
      setTestResults(prev => ({
        ...prev,
        [id]: { success: resData.success, message: resData.message }
      }));

      if (resData.success) {
        notification.success({
          message: "Connection Successful",
          description: resData.message || `Successfully connected to ${id} API.`,
          placement: "bottomRight"
        });
      } else {
        notification.error({
          message: "Connection Failed",
          description: resData.message || `Invalid API credentials for ${id}.`,
          placement: "bottomRight"
        });
      }
    } catch (err: any) {
      console.error(err);
      notification.error({
        message: "Error Testing Connection",
        description: err.message || "Failed to connect to provider servers.",
        placement: "bottomRight"
      });
    } finally {
      setTestingId(null);
    }
  };

  const handleSaveIntegration = async (id: string) => {
    setSavingId(id);
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const { apiKey, webhookUrl } = formStates[id] || { apiKey: "", webhookUrl: "" };

      const response = await fetch(`${API_URL}/integrations/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tokenVal}`
        },
        body: JSON.stringify({ apiKey, webhookUrl })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to save integration details");
      }

      const updated = await response.json();
      setIntegrations(prev => prev.map(item => item.id === id ? updated : item));
      setTestResults(prev => {
        const next = { ...prev };
        delete next[id];
        return next;
      });

      notification.success({
        message: "Integration Saved",
        description: `Successfully updated ${updated.name} settings.`,
        placement: "bottomRight"
      });
    } catch (err: any) {
      console.error(err);
      setTestResults(prev => ({
        ...prev,
        [id]: { success: false, message: err.message || "Failed to save configuration details." }
      }));
      notification.error({
        message: "Error Saving Settings",
        description: err.message || "Failed to save configuration details.",
        placement: "bottomRight"
      });
    } finally {
      setSavingId(null);
    }
  };

  const handleSyncCalls = async (id: string) => {
    setSyncingCallsId(id);
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const response = await fetch(`${API_URL}/integrations/${id}/sync-calls`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${tokenVal}`
        }
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Call sync request failed");
      }

      const resData = await response.json();
      notification.success({
        message: "Calls Synchronized",
        description: resData.message || `Sync finished for ${id}.`,
        placement: "bottomRight"
      });
      fetchIntegrations();
    } catch (err: any) {
      console.error(err);
      notification.error({
        message: "Call Sync Error",
        description: err.message || "Failed to trigger call sync.",
        placement: "bottomRight"
      });
    } finally {
      setSyncingCallsId(null);
    }
  };

  const handleSyncAgents = async (id: string) => {
    setSyncingAgentsId(id);
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const response = await fetch(`${API_URL}/integrations/${id}/sync-agents`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${tokenVal}`
        }
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Agent sync request failed");
      }

      const resData = await response.json();
      notification.success({
        message: "Agents Synchronized",
        description: resData.message || `Agent sync finished for ${id}.`,
        placement: "bottomRight"
      });
    } catch (err: any) {
      console.error(err);
      notification.error({
        message: "Agent Sync Error",
        description: err.message || "Failed to sync agents.",
        placement: "bottomRight"
      });
    } finally {
      setSyncingAgentsId(null);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh" }}>
        <Spin size="large" tip="Loading speech service integrations..." />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "24px" }}>
        <Alert message="Error" description={error} type="error" showIcon />
      </div>
    );
  }

  return (
    <div style={{ padding: "24px", minHeight: "100vh" }}>
      <div style={{ marginBottom: "32px" }}>
        <Title level={2} style={{ margin: 0, fontWeight: 600 }}>Integrations</Title>
        <Text type="secondary">Connect voice AI agent platforms to sync historical calls, agents, and evaluations</Text>
      </div>

      <Row gutter={[24, 24]}>
        {integrations.map((integration) => {
          const info = PROVIDER_INFO[integration.id] || {
            desc: `Connect with ${integration.name} speech evaluations and call transcripts.`,
            color: "#1890ff",
            webhookDesc: "Specify webhook URL settings inside provider configuration."
          };

          const testResult = testResults[integration.id];
          const lastSyncedFormatted = integration.lastSyncedAt 
            ? new Date(integration.lastSyncedAt).toLocaleString() 
            : null;

          return (
            <Col xs={24} lg={12} key={integration.id}>
              <Card
                bordered={false}
                style={{
                  background: token.colorBgContainer,
                  borderRadius: "16px",
                  border: `1px solid ${token.colorBorderSecondary}`,
                  boxShadow: token.boxShadowSecondary,
                  height: "100%"
                }}
                bodyStyle={{ padding: "24px", display: "flex", flexDirection: "column", height: "100%" }}
              >
                {/* Header info */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px" }}>
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <div
                      style={{
                        width: "42px",
                        height: "42px",
                        borderRadius: "10px",
                        background: `rgba(${parseInt(info.color.slice(1, 3), 16)}, ${parseInt(info.color.slice(3, 5), 16)}, ${parseInt(info.color.slice(5, 7), 16)}, 0.12)`,
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        marginRight: "16px",
                        border: `1px solid ${info.color}33`
                      }}
                    >
                      <ApiOutlined style={{ fontSize: "20px", color: info.color }} />
                    </div>
                    <div>
                      <Title level={4} style={{ margin: 0, fontWeight: 600 }}>
                        {integration.name}
                      </Title>
                      <Text type="secondary" style={{ fontSize: "12px" }}>
                        Voice Speech Service
                      </Text>
                    </div>
                  </div>

                  <div style={{ textAlign: "right" }}>
                    <Badge
                      status={integration.connected ? "success" : "default"}
                      text={
                        <span style={{ color: integration.connected ? token.colorSuccess : token.colorTextDescription, fontWeight: 500 }}>
                          {integration.connected ? "Connected" : "Disconnected"}
                        </span>
                      }
                    />
                    {lastSyncedFormatted && (
                      <div style={{ marginTop: "4px" }}>
                        <Text type="secondary" style={{ fontSize: "11px" }}>
                          Last synced: {lastSyncedFormatted}
                        </Text>
                      </div>
                    )}
                  </div>
                </div>

                {/* Card Fields Container */}
                <div style={{ flexGrow: 1, display: "flex", flexDirection: "column", gap: "16px", marginBottom: "24px" }}>
                  <Paragraph style={{ color: token.colorTextSecondary, fontSize: "14px", margin: 0 }}>
                    {info.desc}
                  </Paragraph>

                  {/* API Key Form */}
                  <div>
                    <div style={{ marginBottom: "8px" }}>
                      <Text strong style={{ fontSize: "13px" }}>
                        API Key
                      </Text>
                    </div>
                    <Input.Password
                      placeholder={`Enter ${integration.name} API Key`}
                      value={formStates[integration.id]?.apiKey}
                      onChange={(e) => handleInputChange(integration.id, "apiKey", e.target.value)}
                      prefix={<KeyOutlined style={{ color: token.colorTextPlaceholder, marginRight: "8px" }} />}
                      iconRender={(visible) => (visible ? <EyeTwoTone twoToneColor={info.color} /> : <EyeInvisibleOutlined />)}
                      style={{ borderRadius: "8px" }}
                    />
                  </div>

                  {/* Webhook URL Input */}
                  {integration.id === "vapi" && (
                    <div>
                      <div style={{ marginBottom: "8px" }}>
                        <Text strong style={{ fontSize: "13px" }}>
                          Webhook URL
                        </Text>
                      </div>
                      <Input
                        placeholder="https://your-domain.com/webhook"
                        value={formStates[integration.id]?.webhookUrl}
                        onChange={(e) => handleInputChange(integration.id, "webhookUrl", e.target.value)}
                        prefix={<LinkOutlined style={{ color: token.colorTextPlaceholder, marginRight: "8px" }} />}
                        style={{ borderRadius: "8px" }}
                      />
                      <Text type="secondary" style={{ fontSize: "11px", display: "block", marginTop: "6px", lineHeight: "1.4" }}>
                        {info.webhookDesc}
                      </Text>
                    </div>
                  )}

                  {/* Connection Status Alerts */}
                  {testResult ? (
                    <Alert
                      message={testResult.success ? "Connection verified and active." : "Connection failed."}
                      description={testResult.message}
                      type={testResult.success ? "success" : "error"}
                      showIcon
                      style={{ borderRadius: "8px" }}
                    />
                  ) : (
                    integration.connected && (
                      <Alert
                        message="Connection Active"
                        description="API key verified. Ready for automatic and manual call synchronization."
                        type="success"
                        showIcon
                        style={{ borderRadius: "8px" }}
                      />
                    )
                  )}
                </div>

                {/* Actions Grid */}
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", borderTop: `1px solid ${token.colorBorderSecondary}`, paddingTop: "20px" }}>
                  <div style={{ display: "flex", gap: "12px" }}>
                    <Button
                      onClick={() => handleTestConnection(integration.id)}
                      loading={testingId === integration.id}
                      icon={<ExperimentOutlined />}
                      style={{ flex: 1, borderRadius: "8px" }}
                    >
                      Test Connection
                    </Button>
                    <Button
                      type="primary"
                      onClick={() => handleSaveIntegration(integration.id)}
                      loading={savingId === integration.id}
                      icon={<SaveOutlined />}
                      style={{
                        flex: 1,
                        background: info.color,
                        borderColor: info.color,
                        color: "#fff",
                        borderRadius: "8px",
                        fontWeight: 500
                      }}
                    >
                      Save Settings
                    </Button>
                  </div>

                  {integration.connected && (
                    <div style={{ display: "flex", gap: "12px" }}>
                      <Button
                        onClick={() => handleSyncAgents(integration.id)}
                        loading={syncingAgentsId === integration.id}
                        icon={<SyncOutlined />}
                        style={{ flex: 1, borderRadius: "8px" }}
                      >
                        Sync Agents
                      </Button>
                      <Button
                        onClick={() => handleSyncCalls(integration.id)}
                        loading={syncingCallsId === integration.id}
                        icon={<CloudDownloadOutlined />}
                        style={{
                          flex: 1,
                          borderRadius: "8px",
                          borderColor: info.color,
                          color: info.color,
                          fontWeight: 500
                        }}
                      >
                        Sync Calls
                      </Button>
                    </div>
                  )}
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
};

