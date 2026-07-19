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
  theme
} from "antd";
import {
  MessageOutlined,
  ClockCircleOutlined,
  SoundOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  AlertOutlined,
  RetweetOutlined
} from "@ant-design/icons";
import { API_URL, TOKEN_KEY } from "../../providers/constants";

const { Title, Text } = Typography;

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

const SparkAreaChart: React.FC<{ data: number[]; color: string; label: string; suffix?: string }> = ({ data, color, label, suffix = "" }) => {
  const { token } = theme.useToken();
  if (!data || data.length === 0) return null;
  const width = 500;
  const height = 160;
  const padding = 15;
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

  return (
    <Card 
      bordered={false} 
      style={{ 
        background: token.colorBgContainer, 
        borderRadius: "12px", 
        border: `1px solid ${token.colorBorderSecondary}` 
      }}
      bodyStyle={{ padding: "20px" }}
    >
      <Title level={5} style={{ margin: "0 0 16px 0", fontSize: "15px", fontWeight: 500 }}>
        {label}
      </Title>
      <div style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} style={{ overflow: "visible" }}>
          <defs>
            <linearGradient id={`grad-${label.replace(/\s+/g, "-")}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.25" />
              <stop offset="100%" stopColor={color} stopOpacity="0.0" />
            </linearGradient>
          </defs>
          
          {/* horizontal reference lines */}
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke={token.colorBorderSecondary} strokeWidth="1" />
          <line x1={padding} y1={(height - padding) / 2} x2={width - padding} y2={(height - padding) / 2} stroke={token.colorBorderSecondary} strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
          
          {/* area fill */}
          <path d={areaD} fill={`url(#grad-${label.replace(/\s+/g, "-")})`} />
          
          {/* line path */}
          <path d={pathD} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          
          {/* data circles */}
          {points.map((p, idx) => (
            <Tooltip key={idx} title={`Value: ${p.value}${suffix}`}>
              <circle cx={p.x} cy={p.y} r="4" fill={color} stroke={token.colorBgContainer} strokeWidth="2" style={{ cursor: "pointer" }} />
            </Tooltip>
          ))}
        </svg>
      </div>
    </Card>
  );
};

export const Dashboard: React.FC = () => {
  const { token } = theme.useToken();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState<boolean>(false);

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
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An error occurred while loading dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();

    // Subscribe to Server-Sent Events for real-time synchronization
    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource(`${API_URL.replace("/api/v1", "")}/api/v1/stream`);
      
      eventSource.onopen = () => {
        setIsLive(true);
      };
      
      eventSource.onmessage = (event) => {
        try {
          const rawData = JSON.parse(event.data);
          // If a call ingestion and evaluation completes, automatically refresh the metrics
          if (rawData.type === "conversation_completed") {
            fetchMetrics();
          }
        } catch (e) {
          // Ignore ping frames or JSON parsing errors
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
        <Spin size="large" tip="Loading dashboard metrics..." />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "24px" }}>
        <Alert message="Error" description={error} type="error" showIcon action={
          <Tooltip title="Retry loading metrics">
            <Typography.Link onClick={() => { setLoading(true); fetchMetrics(); }}>Retry</Typography.Link>
          </Tooltip>
        } />
      </div>
    );
  }

  return (
    <div style={{ padding: "24px", minHeight: "100vh" }}>
      {/* Header section */}
      <Row justify="space-between" align="middle" style={{ marginBottom: "24px" }}>
        <Col>
          <Title level={2} style={{ margin: 0, fontWeight: 600 }}>Dashboard</Title>
          <Text type="secondary">Voice Agent Performance Evaluation Insights</Text>
        </Col>
        <Col>
          <Space size="middle">
            <Badge 
              status={isLive ? "success" : "default"} 
              text={
                <Text style={{ fontSize: "13px", color: isLive ? token.colorSuccess : token.colorTextDescription }}>
                  {isLive ? "LIVE SYNC ACTIVE" : "SSE DISCONNECTED"}
                </Text>
              } 
            />
            <Button onClick={fetchMetrics} icon={<RetweetOutlined />}>
              Refresh
            </Button>
          </Space>
        </Col>
      </Row>

      {/* KPI statistics cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} lg={4}>
          <Card bordered={false} style={{ background: token.colorBgContainer, border: `1px solid ${token.colorBorderSecondary}`, borderRadius: "12px" }}>
            <Statistic
              title={<span style={{ color: token.colorTextDescription, fontSize: "13px" }}>Total Calls</span>}
              value={metrics?.conversationsCount}
              prefix={<MessageOutlined style={{ color: "#1890ff", marginRight: "8px" }} />}
              valueStyle={{ fontSize: "24px", fontWeight: 600, color: token.colorText }}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={5}>
          <Card bordered={false} style={{ background: token.colorBgContainer, border: `1px solid ${token.colorBorderSecondary}`, borderRadius: "12px" }}>
            <Statistic
              title={<span style={{ color: token.colorTextDescription, fontSize: "13px" }}>Average Latency</span>}
              value={metrics?.latencyAvg}
              suffix="ms"
              prefix={<ClockCircleOutlined style={{ color: "#faad14", marginRight: "8px" }} />}
              valueStyle={{ fontSize: "24px", fontWeight: 600, color: token.colorText }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={5}>
          <Card bordered={false} style={{ background: token.colorBgContainer, border: `1px solid ${token.colorBorderSecondary}`, borderRadius: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <Statistic
                title={<span style={{ color: token.colorTextDescription, fontSize: "13px" }}>Dead Air Rate</span>}
                value={metrics?.deadAirAvg}
                suffix="%"
                prefix={<SoundOutlined style={{ color: "#ff4d4f", marginRight: "8px" }} />}
                valueStyle={{ fontSize: "24px", fontWeight: 600, color: token.colorText }}
              />
              <Progress 
                type="circle" 
                percent={metrics ? Math.min(100, Math.round(metrics.deadAirAvg * 5)) : 0} 
                width={30} 
                strokeColor="#ff4d4f"
                showInfo={false}
                style={{ marginTop: "4px" }}
              />
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={5}>
          <Card bordered={false} style={{ background: token.colorBgContainer, border: `1px solid ${token.colorBorderSecondary}`, borderRadius: "12px" }}>
            <Statistic
              title={<span style={{ color: token.colorTextDescription, fontSize: "13px" }}>Total Interruptions</span>}
              value={metrics?.interruptionsCount}
              prefix={<WarningOutlined style={{ color: "#fa8c16", marginRight: "8px" }} />}
              valueStyle={{ fontSize: "24px", fontWeight: 600, color: token.colorText }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={5}>
          <Card bordered={false} style={{ background: token.colorBgContainer, border: `1px solid ${token.colorBorderSecondary}`, borderRadius: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <Statistic
                title={<span style={{ color: token.colorTextDescription, fontSize: "13px" }}>Voice Quality</span>}
                value={metrics?.voiceQualityAvg}
                suffix="/100"
                prefix={<CheckCircleOutlined style={{ color: "#52c41a", marginRight: "8px" }} />}
                valueStyle={{ fontSize: "24px", fontWeight: 600, color: token.colorText }}
              />
              <Progress 
                type="circle" 
                percent={metrics?.voiceQualityAvg || 0} 
                width={30} 
                strokeColor="#52c41a"
                showInfo={false}
                style={{ marginTop: "4px" }}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* Main Charts & Alerts grid */}
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <Row gutter={[16, 16]}>
            <Col xs={24}>
              <SparkAreaChart 
                data={metrics?.latencyTrend || []} 
                color="#faad14" 
                label="Agent Response Latency Trend (Last 10 Calls)" 
                suffix="ms" 
              />
            </Col>
            <Col xs={24}>
              <SparkAreaChart 
                data={metrics?.volumeTrend || []} 
                color="#1890ff" 
                label="Call Volume Distribution" 
                suffix=" calls" 
              />
            </Col>
          </Row>
        </Col>
        
        {/* Alerts and anomalies list */}
        <Col xs={24} xl={8}>
          <Card 
            title={
              <Space>
                <AlertOutlined style={{ color: "#ff4d4f" }} />
                <span>Active Alerts & Incidents</span>
              </Space>
            }
            bordered={false}
            style={{ 
              background: token.colorBgContainer, 
              border: `1px solid ${token.colorBorderSecondary}`, 
              borderRadius: "12px",
              height: "100%" 
            }}
            bodyStyle={{ padding: "16px" }}
          >
            {metrics?.activeAlerts && metrics.activeAlerts.length > 0 ? (
              <List
                itemLayout="horizontal"
                dataSource={metrics.activeAlerts}
                renderItem={(item) => (
                  <List.Item style={{ borderBottom: `1px solid ${token.colorBorderSecondary}`, padding: "12px 0" }}>
                    <List.Item.Meta
                      avatar={
                        <Badge 
                          status={item.type === "error" ? "error" : "warning"} 
                          style={{ marginTop: "6px" }}
                        />
                      }
                      title={
                        <Text strong style={{ fontSize: "14px" }}>
                          {item.title}
                        </Text>
                      }
                      description={
                        <Text type="secondary" style={{ fontSize: "12px", display: "block" }}>
                          {item.desc}
                        </Text>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", height: "260px" }}>
                <CheckCircleOutlined style={{ fontSize: "42px", color: "#52c41a", marginBottom: "16px" }} />
                <Text strong>All Systems Nominal</Text>
                <Text type="secondary" style={{ fontSize: "12px" }}>No alert triggers active for this project.</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};
