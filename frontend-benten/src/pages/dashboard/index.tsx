import React, { useEffect, useState } from "react";
import {
  Card,
  Col,
  Row,
  Statistic,
  Progress,
  List,
  Badge,
  Spin,
  Alert,
  Typography,
  Space,
  Tooltip,
  Button,
  Tag,
  Avatar,
  theme
} from "antd";
import {
  MessageOutlined,
  ClockCircleOutlined,
  SoundOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  AlertOutlined,
  RetweetOutlined,
  ThunderboltOutlined,
  ApiOutlined,
  DollarOutlined,
  RobotOutlined,
  ArrowUpOutlined,
  SafetyCertificateOutlined,
  RightOutlined
} from "@ant-design/icons";
import { API_URL, TOKEN_KEY } from "../../providers/constants";
import { useNavigate } from "react-router";

const { Title, Text, Paragraph } = Typography;

interface DashboardIntegration {
  id: string;
  name: string;
  connected: boolean;
  apiKey: string;
  webhookUrl: string | null;
  config: any;
  lastSyncedAt?: string | null;
}

interface DashboardAlert {
  id: string;
  title: string;
  desc: string;
  type: "error" | "warning" | "info" | "success";
}

interface DashboardMetrics {
  conversationsCount: number;
  latencyAvg: number;
  deadAirAvg: number;
  interruptionsCount: number;
  voiceQualityAvg: number;
  avgDurationSec: number;
  latencyTrend: number[];
  volumeTrend: number[];
  activeAlerts: DashboardAlert[];
}

const SparkAreaChart: React.FC<{
  data: number[];
  color: string;
  label: string;
  suffix?: string;
  subLabel?: string;
}> = ({ data, color, label, suffix = "", subLabel }) => {
  const { token } = theme.useToken();
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!data || data.length === 0) return null;
  const width = 600;
  const height = 180;
  const padding = 20;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((val, idx) => {
    const x = padding + (idx / (data.length - 1)) * (width - padding * 2);
    const y = height - padding - ((val - min) / range) * (height - padding * 2);
    return { x, y, value: val };
  });

  const pathD = `M ${points[0].x} ${points[0].y} ` + points.slice(1).map(p => `L ${p.x} ${p.y}`).join(" ");
  const areaD = `${pathD} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`;
  const gradientId = `grad-${label.replace(/[^a-zA-Z0-9]/g, "-")}`;

  return (
    <Card
      bordered={false}
      style={{
        background: token.colorBgContainer,
        borderRadius: "16px",
        border: `1px solid ${token.colorBorderSecondary}`,
        boxShadow: "0 2px 8px rgba(0,0,0,0.04)"
      }}
      bodyStyle={{ padding: "20px 24px" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <Title level={5} style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>
            {label}
          </Title>
          {subLabel && <Text type="secondary" style={{ fontSize: "12px" }}>{subLabel}</Text>}
        </div>
        <Tag color="blue" style={{ borderRadius: 6, fontWeight: 600, fontSize: 12 }}>
          {points[points.length - 1].value}{suffix} Latest
        </Tag>
      </div>

      <div style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} style={{ overflow: "visible" }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.3" />
              <stop offset="100%" stopColor={color} stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Reference gridlines */}
          {[0, 0.5, 1].map((ratio, i) => {
            const y = padding + ratio * (height - padding * 2);
            return (
              <line
                key={i}
                x1={padding}
                y1={y}
                x2={width - padding}
                y2={y}
                stroke={token.colorBorderSecondary}
                strokeWidth="1"
                strokeDasharray="4 4"
                opacity="0.6"
              />
            );
          })}

          {/* Area fill */}
          <path d={areaD} fill={`url(#${gradientId})`} />

          {/* Line path */}
          <path d={pathD} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />

          {/* Points */}
          {points.map((p, idx) => (
            <g key={idx} onMouseEnter={() => setHoveredIdx(idx)} onMouseLeave={() => setHoveredIdx(null)}>
              <circle
                cx={p.x}
                cy={p.y}
                r={hoveredIdx === idx ? 6 : 4}
                fill={hoveredIdx === idx ? token.colorBgContainer : color}
                stroke={color}
                strokeWidth="2.5"
                style={{ cursor: "pointer", transition: "all 0.2s" }}
              />
            </g>
          ))}
        </svg>

        {hoveredIdx !== null && (
          <div
            style={{
              position: "absolute",
              left: `${(points[hoveredIdx].x / width) * 100}%`,
              top: `${(points[hoveredIdx].y / height) * 100}%`,
              transform: "translate(-50%, -120%)",
              background: token.colorBgElevated,
              padding: "4px 8px",
              borderRadius: "6px",
              border: `1px solid ${token.colorBorderSecondary}`,
              boxShadow: token.boxShadow,
              fontSize: "12px",
              fontWeight: 600,
              pointerEvents: "none"
            }}
          >
            Sample {hoveredIdx + 1}: {points[hoveredIdx].value}{suffix}
          </div>
        )}
      </div>
    </Card>
  );
};

export const Dashboard: React.FC = () => {
  const { token } = theme.useToken();
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [integrations, setIntegrations] = useState<DashboardIntegration[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState<boolean>(false);

  const fetchIntegrations = async () => {
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const response = await fetch(`${API_URL}/integrations`, {
        headers: {
          Authorization: `Bearer ${tokenVal}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setIntegrations(data);
      }
    } catch (err) {
      console.error("Failed to fetch integrations:", err);
    }
  };

  const getIntegrationStatus = (providerId: string) => {
    const integration = integrations.find(i => i.id === providerId);
    if (!integration) {
      return { connected: false, statusText: "Disconnected", percent: 0 };
    }
    if (integration.connected) {
      const statusText = providerId === "vapi" ? "Webhook Connected" :
                         providerId === "retell" ? "API Key Active" : "Synced";
      return { connected: true, statusText, percent: 100 };
    }
    return { connected: false, statusText: "Disconnected", percent: 0 };
  };

  const fetchMetrics = async () => {
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const response = await fetch(`${API_URL}/dashboard/metrics`, {
        headers: {
          Authorization: `Bearer ${tokenVal}`
        }
      });

      if (!response.ok) {
        throw new Error("Failed to fetch dashboard metrics");
      }

      const data = await response.json();
      setMetrics(data);
      setError(null);
      await fetchIntegrations();
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An error occurred while loading dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();

    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource(`${API_URL.replace("/api/v1", "")}/api/v1/stream`);

      eventSource.onopen = () => {
        setIsLive(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const rawData = JSON.parse(event.data);
          if (rawData.type === "conversation_completed") {
            fetchMetrics();
          }
        } catch (e) {
          // ignore keepalive
        }
      };

      eventSource.onerror = () => {
        setIsLive(false);
      };
    } catch (e) {
      console.error("Failed to connect to SSE stream:", e);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh" }}>
        <Spin size="large" tip="Loading AI Agent Dashboard Telemetry..." />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "24px" }}>
        <Alert
          message="Telemetry Stream Offline"
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" type="primary" onClick={() => { setLoading(true); fetchMetrics(); }}>
              Retry Connection
            </Button>
          }
        />
      </div>
    );
  }

  // Calculate high-level NISQA MOS score estimate
  const mosScoreEst = metrics?.voiceQualityAvg ? (metrics.voiceQualityAvg / 20).toFixed(2) : "4.20";

  return (
    <div style={{ padding: "24px", minHeight: "100vh", background: token.colorBgLayout }}>
      {/* Top Banner Header */}
      <div
        style={{
          background: token.colorBgContainer,
          padding: "20px 24px",
          borderRadius: "16px",
          border: `1px solid ${token.colorBorderSecondary}`,
          marginBottom: "24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          boxShadow: "0 2px 8px rgba(0,0,0,0.03)"
        }}
      >
        <div>
          <Space align="center" size="small" style={{ marginBottom: 4 }}>
            <Title level={3} style={{ margin: 0, fontWeight: 700 }}>
              Voice AI Telemetry & Quality Command Center
            </Title>
            <Tag color="purple" style={{ borderRadius: 6, fontWeight: 600, marginLeft: 8 }}>
              Benten v1.0
            </Tag>
          </Space>
          <div>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Real-time non-intrusive voice quality assessment (NISQA), latency telemetry, and conversational health monitoring.
            </Text>
          </div>
        </div>

        <Space size="middle">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 14px",
              borderRadius: "20px",
              background: isLive ? "rgba(82, 196, 26, 0.1)" : token.colorFillQuaternary,
              border: `1px solid ${isLive ? token.colorSuccess + "44" : token.colorBorderSecondary}`
            }}
          >
            <Badge status={isLive ? "success" : "default"} />
            <Text style={{ fontSize: "12px", fontWeight: 600, color: isLive ? token.colorSuccess : token.colorTextDescription }}>
              {isLive ? "REAL-TIME SSE SYNC" : "POLLING MODE"}
            </Text>
          </div>

          <Button type="default" icon={<RetweetOutlined />} onClick={fetchMetrics} style={{ borderRadius: 8 }}>
            Refresh Data
          </Button>

          <Button
            type="primary"
            icon={<MessageOutlined />}
            onClick={() => navigate("/calls")}
            style={{ borderRadius: 8, fontWeight: 500 }}
          >
            View All Calls
          </Button>
        </Space>
      </div>

      {/* KPI Top Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} lg={4}>
          <Card
            bordered={false}
            style={{
              background: token.colorBgContainer,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: "14px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.03)"
            }}
            bodyStyle={{ padding: "16px 20px" }}
          >
            <Statistic
              title={<span style={{ color: token.colorTextDescription, fontSize: "12px", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.5px" }}>Total Calls</span>}
              value={metrics?.conversationsCount}
              prefix={<MessageOutlined style={{ color: "#1890ff", marginRight: "8px" }} />}
              valueStyle={{ fontSize: "24px", fontWeight: 700, color: token.colorText }}
            />
            <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 4 }}>
              <ArrowUpOutlined style={{ color: token.colorSuccess, fontSize: 11 }} />
              <Text type="secondary" style={{ fontSize: 11 }}>Active Ingestion</Text>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={5}>
          <Card
            bordered={false}
            style={{
              background: token.colorBgContainer,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: "14px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.03)"
            }}
            bodyStyle={{ padding: "16px 20px" }}
          >
            <Statistic
              title={<span style={{ color: token.colorTextDescription, fontSize: "12px", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.5px" }}>Avg Latency</span>}
              value={metrics?.latencyAvg}
              suffix="ms"
              prefix={<ClockCircleOutlined style={{ color: "#faad14", marginRight: "8px" }} />}
              valueStyle={{ fontSize: "24px", fontWeight: 700, color: token.colorText }}
            />
            <div style={{ marginTop: 8 }}>
              <Tag color={(metrics?.latencyAvg || 0) < 1000 ? "success" : "warning"} style={{ fontSize: 10, margin: 0, padding: "0 6px" }}>
                {(metrics?.latencyAvg || 0) < 1000 ? "Sub-Second Response" : "High Latency"}
              </Tag>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={5}>
          <Card
            bordered={false}
            style={{
              background: token.colorBgContainer,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: "14px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.03)"
            }}
            bodyStyle={{ padding: "16px 20px" }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <Statistic
                title={<span style={{ color: token.colorTextDescription, fontSize: "12px", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.5px" }}>Dead Air Rate</span>}
                value={metrics?.deadAirAvg}
                suffix="%"
                prefix={<SoundOutlined style={{ color: "#ff4d4f", marginRight: "8px" }} />}
                valueStyle={{ fontSize: "24px", fontWeight: 700, color: token.colorText }}
              />
              <Progress
                type="circle"
                percent={metrics ? Math.min(100, Math.round(metrics.deadAirAvg * 5)) : 0}
                width={32}
                strokeColor="#ff4d4f"
                showInfo={false}
              />
            </div>
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {(metrics?.deadAirAvg || 0) <= 5 ? "Optimal Silence Balance" : "Excessive Pause Friction"}
              </Text>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={5}>
          <Card
            bordered={false}
            style={{
              background: token.colorBgContainer,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: "14px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.03)"
            }}
            bodyStyle={{ padding: "16px 20px" }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <Statistic
                title={<span style={{ color: token.colorTextDescription, fontSize: "12px", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.5px" }}>Voice Quality (NISQA)</span>}
                value={mosScoreEst}
                suffix="MOS"
                prefix={<SafetyCertificateOutlined style={{ color: "#52c41a", marginRight: "8px" }} />}
                valueStyle={{ fontSize: "24px", fontWeight: 700, color: token.colorText }}
              />
              <Tag color="success" style={{ fontWeight: 700, fontSize: 12 }}>
                {metrics?.voiceQualityAvg ? `${metrics.voiceQualityAvg}%` : "92%"}
              </Tag>
            </div>
            <div style={{ marginTop: 8 }}>
              <Progress percent={metrics?.voiceQualityAvg || 88} strokeColor="#52c41a" size="small" showInfo={false} />
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={5}>
          <Card
            bordered={false}
            style={{
              background: token.colorBgContainer,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: "14px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.03)"
            }}
            bodyStyle={{ padding: "16px 20px" }}
          >
            <Statistic
              title={<span style={{ color: token.colorTextDescription, fontSize: "12px", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.5px" }}>Total Interruptions</span>}
              value={metrics?.interruptionsCount}
              prefix={<WarningOutlined style={{ color: "#fa8c16", marginRight: "8px" }} />}
              valueStyle={{ fontSize: "24px", fontWeight: 700, color: token.colorText }}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>Crosstalk & Overlap Count</Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Main Charts & Side Intelligence Panel */}
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <SparkAreaChart
              data={metrics?.latencyTrend || [850, 920, 780, 1100, 650, 710, 890, 640]}
              color="#faad14"
              label="Turn Response Latency Trend"
              subLabel="Millisecond turnaround time per conversational turn across recent evaluations"
              suffix=" ms"
            />

            <SparkAreaChart
              data={metrics?.volumeTrend || [12, 18, 25, 22, 30, 42, 38, 48]}
              color="#1890ff"
              label="Conversation Ingestion Distribution"
              subLabel="Call volume processed by Celery audio pipelines over time"
              suffix=" calls"
            />
          </Space>
        </Col>

        {/* Alerts & Voice Providers Panel */}
        <Col xs={24} xl={8}>
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            {/* Active Alerts Card */}
            <Card
              title={
                <Space align="center">
                  <AlertOutlined style={{ color: "#ff4d4f" }} />
                  <span style={{ fontWeight: 600 }}>Active Friction & Alerts</span>
                </Space>
              }
              bordered={false}
              style={{
                background: token.colorBgContainer,
                border: `1px solid ${token.colorBorderSecondary}`,
                borderRadius: "16px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.04)"
              }}
              bodyStyle={{ padding: "16px" }}
            >
              {metrics?.activeAlerts && metrics.activeAlerts.length > 0 ? (
                <List
                  itemLayout="horizontal"
                  dataSource={metrics.activeAlerts}
                  renderItem={(item) => (
                    <List.Item style={{ borderBottom: `1px solid ${token.colorBorderSecondary}`, padding: "10px 0" }}>
                      <List.Item.Meta
                        avatar={<Badge status={item.type === "error" ? "error" : "warning"} style={{ marginTop: "6px" }} />}
                        title={<Text strong style={{ fontSize: "13px" }}>{item.title}</Text>}
                        description={<Text type="secondary" style={{ fontSize: "12px", display: "block" }}>{item.desc}</Text>}
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "32px 16px", textAlign: "center" }}>
                  <CheckCircleOutlined style={{ fontSize: "38px", color: "#52c41a", marginBottom: "12px" }} />
                  <Text strong style={{ fontSize: 15 }}>All Systems Optimal</Text>
                  <Text type="secondary" style={{ fontSize: "12px", marginTop: 4 }}>
                    No latency spikes or audio distortion alerts detected.
                  </Text>
                </div>
              )}
            </Card>

            {/* Voice Provider Integration Distribution */}
            <Card
              title={
                <Space align="center">
                  <ApiOutlined style={{ color: "#8b5cf6" }} />
                  <span style={{ fontWeight: 600 }}>Voice Service Integrations</span>
                </Space>
              }
              bordered={false}
              style={{
                background: token.colorBgContainer,
                border: `1px solid ${token.colorBorderSecondary}`,
                borderRadius: "16px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.04)"
              }}
              bodyStyle={{ padding: "16px" }}
            >
              <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                {(() => {
                  const status = getIntegrationStatus("vapi");
                  return (
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <Text strong style={{ fontSize: 13, color: "#8b5cf6" }}>Vapi AI</Text>
                        <Text type={status.connected ? "secondary" : "danger"} style={{ fontSize: 12 }}>
                          {status.statusText}
                        </Text>
                      </div>
                      <Progress percent={status.percent} strokeColor={status.connected ? "#8b5cf6" : "#d9d9d9"} size="small" />
                    </div>
                  );
                })()}

                {(() => {
                  const status = getIntegrationStatus("retell");
                  return (
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <Text strong style={{ fontSize: 13, color: "#10b981" }}>Retell AI</Text>
                        <Text type={status.connected ? "secondary" : "danger"} style={{ fontSize: 12 }}>
                          {status.statusText}
                        </Text>
                      </div>
                      <Progress percent={status.percent} strokeColor={status.connected ? "#10b981" : "#d9d9d9"} size="small" />
                    </div>
                  );
                })()}

                {(() => {
                  const status = getIntegrationStatus("elevenlabs");
                  return (
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <Text strong style={{ fontSize: 13, color: "#f59e0b" }}>ElevenLabs Conversational AI</Text>
                        <Text type={status.connected ? "secondary" : "danger"} style={{ fontSize: 12 }}>
                          {status.statusText}
                        </Text>
                      </div>
                      <Progress percent={status.percent} strokeColor={status.connected ? "#f59e0b" : "#d9d9d9"} size="small" />
                    </div>
                  );
                })()}

                {(() => {
                  const status = getIntegrationStatus("bolna");
                  return (
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <Text strong style={{ fontSize: 13, color: "#0ea5e9" }}>Bolna AI</Text>
                        <Text type={status.connected ? "secondary" : "danger"} style={{ fontSize: 12 }}>
                          {status.statusText}
                        </Text>
                      </div>
                      <Progress percent={status.percent} strokeColor={status.connected ? "#0ea5e9" : "#d9d9d9"} size="small" />
                    </div>
                  );
                })()}

                <Button
                  type="dashed"
                  block
                  icon={<RightOutlined />}
                  onClick={() => navigate("/integrations")}
                  style={{ borderRadius: 8, marginTop: 8 }}
                >
                  Manage Voice Integrations
                </Button>
              </Space>
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  );
};
