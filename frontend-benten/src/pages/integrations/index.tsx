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
  Tag,
  Tooltip,
  Collapse,
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
  EyeTwoTone,
  CopyOutlined,
  CheckOutlined,
  QuestionCircleOutlined,
  SafetyCertificateOutlined,
  GlobalOutlined,
  CheckCircleOutlined
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

const PROVIDER_INFO: Record<string, { desc: string; color: string; webhookDesc: string; setupSteps: string[] }> = {
  vapi: {
    desc: "Benten automatically ingests call recordings, transcripts, and turn-by-turn latency metrics via Vapi's webhook event payload.",
    color: "#8b5cf6",
    webhookDesc: "Set this Webhook URL in your Vapi Dashboard under Account Settings -> Webhooks.",
    setupSteps: [
      "Open your Vapi Dashboard (dashboard.vapi.ai) and navigate to Account -> Webhooks.",
      "Paste the Webhook Endpoint URL into the Server URL field.",
      "Ensure 'end-of-call-report' events are enabled.",
      "Paste your Vapi Private API Key below to enable manual historical sync."
    ]
  },
  retell: {
    desc: "Fetch agent responses, latency logs, and voice conversation transcripts from your Retell AI account.",
    color: "#10b981",
    webhookDesc: "Configure this webhook URL inside your Retell AI Developer Settings.",
    setupSteps: [
      "Log into your Retell AI Dashboard and navigate to API & Integrations.",
      "Copy your Retell API Key and paste it into the input below.",
      "Click 'Test Connection' to verify API key permissions.",
      "Use 'Sync Agents' and 'Sync Calls' to fetch historical conversation logs."
    ]
  },
  elevenlabs: {
    desc: "Ingest custom agent profiles, speech synthesis audio, and voice performance parameters from ElevenLabs Conversational AI.",
    color: "#f59e0b",
    webhookDesc: "Provide this Webhook endpoint inside ElevenLabs agent developer settings.",
    setupSteps: [
      "Navigate to ElevenLabs Conversational AI Platform Settings -> API Keys.",
      "Generate a new API Key with read/write access.",
      "Paste your ElevenLabs API key below and save settings.",
      "Click 'Sync Calls' to download agent audio recordings."
    ]
  }
};

export const IntegrationsPage: React.FC = () => {
  const { token } = theme.useToken();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [formStates, setFormStates] = useState<Record<string, { apiKey: string; webhookUrl: string }>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [syncingCallsId, setSyncingCallsId] = useState<string | null>(null);
  const [syncingAgentsId, setSyncingAgentsId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

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

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    notification.success({
      message: "Copied to Clipboard",
      description: "Webhook URL copied successfully.",
      placement: "bottomRight"
    });
    setTimeout(() => setCopiedId(null), 2000);
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
          message: "Connection Verified",
          description: resData.message || `Successfully validated connection to ${id}.`,
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
        description: err.message || "Failed to reach provider endpoint.",
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
        message: "Integration Settings Saved",
        description: `Successfully updated ${updated.name} credentials.`,
        placement: "bottomRight"
      });
    } catch (err: any) {
      console.error(err);
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
        description: resData.message || `Sync completed for ${id}.`,
        placement: "bottomRight"
      });
      fetchIntegrations();
    } catch (err: any) {
      console.error(err);
      notification.error({
        message: "Call Sync Error",
        description: err.message || "Failed to sync provider call records.",
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
        <Spin size="large" tip="Loading Voice Integration Hub..." />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "24px" }}>
        <Alert message="Error Loading Integrations" description={error} type="error" showIcon />
      </div>
    );
  }

  const activeCount = integrations.filter(i => i.connected).length;

  return (
    <div style={{ padding: "24px", minHeight: "100vh", background: token.colorBgLayout }}>
      {/* Header Banner */}
      <div
        style={{
          background: token.colorBgContainer,
          padding: "24px",
          borderRadius: "16px",
          border: `1px solid ${token.colorBorderSecondary}`,
          marginBottom: "32px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.03)"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <Title level={2} style={{ margin: 0, fontWeight: 700 }}>
              Voice Service Integrations
            </Title>
            <Text type="secondary" style={{ fontSize: 14 }}>
              Connect Vapi, Retell, and ElevenLabs to automatically ingest conversations, sync agent profiles, and analyze speech metrics.
            </Text>
          </div>

          <Space size="middle">
            <Tag color="purple" style={{ padding: "6px 12px", borderRadius: 8, fontSize: 13, fontWeight: 600 }}>
              <ApiOutlined style={{ marginRight: 6 }} />
              {integrations.length} Supported Providers
            </Tag>
            <Tag color="success" style={{ padding: "6px 12px", borderRadius: 8, fontSize: 13, fontWeight: 600 }}>
              <CheckCircleOutlined style={{ marginRight: 6 }} />
              {activeCount} Active Connections
            </Tag>
          </Space>
        </div>
      </div>

      {/* Provider Grid */}
      <Row gutter={[24, 24]}>
        {integrations.map((integration) => {
          const info = PROVIDER_INFO[integration.id] || {
            desc: `Connect with ${integration.name} speech evaluations and call transcripts.`,
            color: "#1890ff",
            webhookDesc: "Specify webhook URL settings inside provider configuration.",
            setupSteps: ["Configure API Key and save settings."]
          };

          const testResult = testResults[integration.id];
          const lastSyncedFormatted = integration.lastSyncedAt
            ? new Date(integration.lastSyncedAt).toLocaleString()
            : null;

          const defaultWebhook = `${window.location.origin.replace(":5173", ":8000")}/api/v1/conversations/webhook/${integration.id}`;

          return (
            <Col xs={24} lg={12} key={integration.id}>
              <Card
                bordered={false}
                style={{
                  background: token.colorBgContainer,
                  borderRadius: "16px",
                  border: `1px solid ${token.colorBorderSecondary}`,
                  boxShadow: "0 4px 12px rgba(0,0,0,0.04)",
                  height: "100%"
                }}
                bodyStyle={{ padding: "24px", display: "flex", flexDirection: "column", height: "100%" }}
              >
                {/* Provider Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px" }}>
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <div
                      style={{
                        width: "48px",
                        height: "48px",
                        borderRadius: "12px",
                        background: `rgba(${parseInt(info.color.slice(1, 3), 16)}, ${parseInt(info.color.slice(3, 5), 16)}, ${parseInt(info.color.slice(5, 7), 16)}, 0.12)`,
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        marginRight: "16px",
                        border: `1.5px solid ${info.color}44`
                      }}
                    >
                      <ApiOutlined style={{ fontSize: "24px", color: info.color }} />
                    </div>
                    <div>
                      <Title level={4} style={{ margin: 0, fontWeight: 700 }}>
                        {integration.name}
                      </Title>
                      <Text type="secondary" style={{ fontSize: "12px", fontWeight: 500 }}>
                        Voice Telemetry Provider
                      </Text>
                    </div>
                  </div>

                  <div style={{ textAlign: "right" }}>
                    <Badge
                      status={integration.connected ? "success" : "default"}
                      text={
                        <span style={{ color: integration.connected ? token.colorSuccess : token.colorTextDescription, fontWeight: 600 }}>
                          {integration.connected ? "Active Connection" : "Not Configured"}
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

                {/* Body Content */}
                <div style={{ flexGrow: 1, display: "flex", flexDirection: "column", gap: "16px", marginBottom: "24px" }}>
                  <Paragraph style={{ color: token.colorTextSecondary, fontSize: "13.5px", margin: 0, lineHeight: 1.5 }}>
                    {info.desc}
                  </Paragraph>

                  {/* API Key Field */}
                  <div>
                    <div style={{ marginBottom: "6px" }}>
                      <Text strong style={{ fontSize: "13px" }}>
                        API Secret Key
                      </Text>
                    </div>
                    <Input.Password
                      placeholder={`Enter ${integration.name} Private API Key...`}
                      value={formStates[integration.id]?.apiKey}
                      onChange={(e) => handleInputChange(integration.id, "apiKey", e.target.value)}
                      prefix={<KeyOutlined style={{ color: token.colorTextPlaceholder, marginRight: "8px" }} />}
                      iconRender={(visible) => (visible ? <EyeTwoTone twoToneColor={info.color} /> : <EyeInvisibleOutlined />)}
                      style={{ borderRadius: "8px" }}
                    />
                  </div>

                  {/* Webhook Endpoint Box */}
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <Text strong style={{ fontSize: "13px" }}>
                        Inbound Webhook Endpoint
                      </Text>
                      <Button
                        type="link"
                        size="small"
                        icon={copiedId === integration.id ? <CheckOutlined style={{ color: token.colorSuccess }} /> : <CopyOutlined />}
                        onClick={() => copyToClipboard(formStates[integration.id]?.webhookUrl || defaultWebhook, integration.id)}
                        style={{ fontSize: 12, padding: 0 }}
                      >
                        {copiedId === integration.id ? "Copied" : "Copy Endpoint"}
                      </Button>
                    </div>
                    <Input
                      readOnly
                      value={formStates[integration.id]?.webhookUrl || defaultWebhook}
                      prefix={<LinkOutlined style={{ color: token.colorTextPlaceholder, marginRight: "8px" }} />}
                      style={{ borderRadius: "8px", background: token.colorFillQuaternary, cursor: "pointer" }}
                      onClick={() => copyToClipboard(formStates[integration.id]?.webhookUrl || defaultWebhook, integration.id)}
                    />
                    <Text type="secondary" style={{ fontSize: "11px", display: "block", marginTop: "6px", lineHeight: "1.4" }}>
                      {info.webhookDesc}
                    </Text>
                  </div>

                  {/* Test Connection Result Alert */}
                  {testResult ? (
                    <Alert
                      message={testResult.success ? "Connection Verified" : "Authentication Failed"}
                      description={testResult.message}
                      type={testResult.success ? "success" : "error"}
                      showIcon
                      style={{ borderRadius: "8px" }}
                    />
                  ) : null}

                  {/* Quick Setup Instructions Accordion */}
                  <Collapse
                    ghost
                    size="small"
                    items={[
                      {
                        key: "setup",
                        label: (
                          <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>
                            <QuestionCircleOutlined style={{ marginRight: 6 }} /> Quick Setup Instructions
                          </Text>
                        ),
                        children: (
                          <ol style={{ paddingLeft: 20, margin: 0, fontSize: 12, color: token.colorTextSecondary }}>
                            {info.setupSteps.map((step, idx) => (
                              <li key={idx} style={{ marginBottom: 4 }}>{step}</li>
                            ))}
                          </ol>
                        )
                      }
                    ]}
                  />
                </div>

                {/* Actions Toolbar */}
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
                        fontWeight: 600
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
                          fontWeight: 600
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
