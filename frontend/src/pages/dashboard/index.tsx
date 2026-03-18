import React from "react";
import { Row, Col, Card, Statistic, Alert, List, Tag, Typography, Space, Tooltip, Progress, Button } from "antd";
import {
  DashboardOutlined,
  ClockCircleOutlined,
  SoundOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  HourglassOutlined,
  InfoCircleOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  AudioOutlined
} from "@ant-design/icons";

const { Title, Text, Paragraph } = Typography;

export const Dashboard: React.FC = () => {
  // Latency data points: 24h trend
  const latencyTrend = [450, 430, 440, 410, 415, 395, 410, 420, 405, 410];
  // Volume data points: 24h trend
  const volumeTrend = [180, 220, 240, 210, 230, 195, 241, 260, 250, 270];

  const renderSparkline = (data: number[], color: string) => {
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const width = 300;
    const height = 60;
    const points = data
      .map((val, idx) => {
        const x = (idx / (data.length - 1)) * width;
        const y = height - ((val - min) / range) * (height - 10) - 5;
        return `${x},${y}`;
      })
      .join(" ");

    return (
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.4" />
            <stop offset="100%" stopColor={color} stopOpacity="0.0" />
          </linearGradient>
        </defs>
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="3"
          points={points}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <polygon
          points={`0,${height} ${points} ${width},${height}`}
          fill={`url(#grad-${color})`}
        />
      </svg>
    );
  };

  const topAlerts = [
    { title: "High latency on Sales Agent", desc: "Response latency spiked to 950ms", type: "warning" },
    { title: "Voice quality degraded", desc: "Mean Opinion Score dropped to 3.5 on Support Agent", type: "error" },
    { title: "Dead air increased by 14%", desc: "Dead air percentage hit 11% on Support Agent", type: "warning" },
  ];

  const quickAnswers = [
    {
      q: "Is everything healthy?",
      a: "No. The Support Agent is currently flagging a Warning status due to an 11% dead air spike and high webhook latency (Avg 980ms). Sales and Clinic agents remain healthy.",
      status: "warning",
    },
    {
      q: "Which agent has problems?",
      a: "Support Agent (Vapi provider) is experiencing degraded performance. Sales Agent is showing minor latency spikes but remains overall healthy (95% score).",
      status: "error",
    },
    {
      q: "Is latency increasing?",
      a: "Yes, latency on the Support Agent has steadily climbed from 750ms to 980ms over the last 6 hours, likely due to downstream webhook response delays.",
      status: "info",
    },
    {
      q: "Did today's deployment break anything?",
      a: "Possibly. The dead air and latency spikes on the Support Agent correlate with the v2.4.1 deployment made today at 08:00 UTC.",
      status: "warning",
    },
  ];

  return (
    <div style={{ padding: "4px" }}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div>
              <Title level={2} style={{ margin: 0 }}>VoiceOps Dashboard</Title>
              <Text type="secondary">High-level view of your AI voice agents health in the last 24 hours.</Text>
            </div>
            <Tag color="processing" style={{ padding: "4px 12px", fontSize: "14px" }}>
              <ClockCircleOutlined /> Live Feed: Active
            </Tag>
          </div>
        </Col>

        {/* METRICS ROW */}
        <Col xs={12} sm={8} lg={4}>
          <Card bordered={false} hoverable style={{ background: "rgba(255, 255, 255, 0.05)", backdropFilter: "blur(8px)" }}>
            <Statistic
              title={<span style={{ fontSize: "14px", fontWeight: 500 }}><AudioOutlined /> Conversations</span>}
              value={2341}
              valueStyle={{ fontSize: "28px", fontWeight: "bold" }}
            />
            <Text type="success" style={{ fontSize: "12px" }}>+12% vs yesterday</Text>
          </Card>
        </Col>

        <Col xs={12} sm={8} lg={4}>
          <Card bordered={false} hoverable>
            <Statistic
              title={<span style={{ fontSize: "14px", fontWeight: 500 }}><ClockCircleOutlined /> Avg Latency</span>}
              value={410}
              suffix="ms"
              valueStyle={{ fontSize: "28px", fontWeight: "bold" }}
            />
            <Text type="danger" style={{ fontSize: "12px" }}>+45ms (spiked at 10 AM)</Text>
          </Card>
        </Col>

        <Col xs={12} sm={8} lg={4}>
          <Card bordered={false} hoverable>
            <Statistic
              title={<span style={{ fontSize: "14px", fontWeight: 500 }}><SoundOutlined /> Dead Air</span>}
              value={3.2}
              suffix="%"
              valueStyle={{ fontSize: "28px", fontWeight: "bold" }}
            />
            <Progress percent={32} showInfo={false} size="small" status="active" strokeColor="#faad14" />
          </Card>
        </Col>

        <Col xs={12} sm={8} lg={4}>
          <Card bordered={false} hoverable>
            <Statistic
              title={<span style={{ fontSize: "14px", fontWeight: 500 }}><CloseCircleOutlined /> Interruptions</span>}
              value={187}
              valueStyle={{ fontSize: "28px", fontWeight: "bold" }}
            />
            <Text type="warning" style={{ fontSize: "12px" }}>Barge-in rate: 7.9%</Text>
          </Card>
        </Col>

        <Col xs={12} sm={8} lg={4}>
          <Card bordered={false} hoverable>
            <Statistic
              title={<span style={{ fontSize: "14px", fontWeight: 500 }}><SafetyCertificateOutlined /> Voice Quality</span>}
              value={92}
              suffix="%"
              valueStyle={{ fontSize: "28px", fontWeight: "bold" }}
            />
            <Progress percent={92} showInfo={false} size="small" status="success" strokeColor="#52c41a" />
          </Card>
        </Col>

        <Col xs={12} sm={8} lg={4}>
          <Card bordered={false} hoverable>
            <Statistic
              title={<span style={{ fontSize: "14px", fontWeight: 500 }}><HourglassOutlined /> Avg Duration</span>}
              value="3m 42s"
              valueStyle={{ fontSize: "24px", fontWeight: "bold" }}
            />
            <Text type="secondary" style={{ fontSize: "12px" }}>Peak length: 14m 12s</Text>
          </Card>
        </Col>

        {/* TRENDS & ALERTS */}
        <Col xs={24} lg={16}>
          <Card title="Performance Trends" bordered={false} style={{ height: "100%" }}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <div style={{ marginBottom: "12px" }}>
                  <Text strong style={{ fontSize: "15px" }}>Avg Latency Trend (24 Hours)</Text>
                </div>
                <div style={{ border: "1px solid rgba(0,0,0,0.06)", borderRadius: "8px", padding: "16px", background: "rgba(0,0,0,0.02)" }}>
                  {renderSparkline(latencyTrend, "#1890ff")}
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px" }}>
                    <Text type="secondary" style={{ fontSize: "12px" }}>24h ago (450ms)</Text>
                    <Text strong style={{ fontSize: "12px", color: "#1890ff" }}>Current: 410ms</Text>
                  </div>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ marginBottom: "12px" }}>
                  <Text strong style={{ fontSize: "15px" }}>Conversation Volume Trend (24 Hours)</Text>
                </div>
                <div style={{ border: "1px solid rgba(0,0,0,0.06)", borderRadius: "8px", padding: "16px", background: "rgba(0,0,0,0.02)" }}>
                  {renderSparkline(volumeTrend, "#52c41a")}
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px" }}>
                    <Text type="secondary" style={{ fontSize: "12px" }}>24h ago (180)</Text>
                    <Text strong style={{ fontSize: "12px", color: "#52c41a" }}>Current: 270</Text>
                  </div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title={<Space><AlertOutlined style={{ color: "#ff4d4f" }} /><span>Top Active Alerts</span></Space>} bordered={false} style={{ height: "100%" }}>
            <List
              dataSource={topAlerts}
              renderItem={(item) => (
                <List.Item style={{ padding: "10px 0" }}>
                  <Space align="start">
                    <Tag color={item.type === "error" ? "error" : "warning"}>
                      {item.type.toUpperCase()}
                    </Tag>
                    <div>
                      <Text strong>{item.title}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: "12px" }}>{item.desc}</Text>
                    </div>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* HEALTH QUESTIONS */}
        <Col span={24}>
          <Card title={<Space><InfoCircleOutlined /><span>Voice Agent Health Assistant</span></Space>} bordered={false}>
            <Row gutter={[16, 16]}>
              {quickAnswers.map((qa, index) => (
                <Col xs={24} md={12} key={index}>
                  <Card size="small" type="inner" style={{ borderLeft: `4px solid ${qa.status === "error" ? "#ff4d4f" : qa.status === "warning" ? "#faad14" : "#1890ff"}` }}>
                    <Paragraph strong style={{ marginBottom: "6px" }}>{qa.q}</Paragraph>
                    <Paragraph style={{ margin: 0, fontSize: "13px" }} type="secondary">{qa.a}</Paragraph>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

// Activity: simulated update on 2026-03-18
