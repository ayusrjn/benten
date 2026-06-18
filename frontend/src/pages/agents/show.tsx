import React from "react";
import { Row, Col, Card, Statistic, Tag, Button, Typography, Space, Progress, List, Table } from "antd";
import { ArrowLeftOutlined, AlertOutlined, SafetyCertificateOutlined, WarningOutlined, AudioOutlined } from "@ant-design/icons";
import { useParams, useNavigate } from "react-router";
import { mockAgents, mockConversations } from "../../providers/mockData";

const { Title, Text, Paragraph } = Typography;

export const AgentShow: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Find agent in mock data
  const agent = mockAgents.find((a) => a.id === id) || mockAgents[0];

  // Get conversations for this agent
  const agentConversations = mockConversations.filter((c) => c.agentId === agent.id);

  // Helper to draw mini sparkline
  const renderTrendSvg = (data: number[], color: string, suffix: string = "") => {
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const width = 200;
    const height = 50;
    const points = data
      .map((val, idx) => {
        const x = (idx / (data.length - 1)) * width;
        const y = height - ((val - min) / range) * (height - 10) - 5;
        return `${x},${y}`;
      })
      .join(" ");

    return (
      <div style={{ marginTop: "10px", background: "rgba(0,0,0,0.02)", padding: "10px", borderRadius: "6px" }}>
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
          <polyline
            fill="none"
            stroke={color}
            strokeWidth="2"
            points={points}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "4px", fontSize: "11px" }}>
          <Text type="secondary">Initial: {data[0]}{suffix}</Text>
          <Text strong style={{ color }}>Current: {data[data.length - 1]}{suffix}</Text>
        </div>
      </div>
    );
  };

  const columns = [
    {
      title: "Conversation ID",
      dataIndex: "id",
      key: "id",
      render: (text: string) => <Button type="link" onClick={() => navigate(`/conversations/show/${text}`)} style={{ padding: 0 }}>#{text}</Button>,
    },
    {
      title: "Evaluation Score",
      dataIndex: "score",
      key: "score",
      render: (score: number) => <Tag color={score >= 85 ? "success" : "warning"}>{score}/100</Tag>,
    },
    {
      title: "Duration",
      dataIndex: "duration",
      key: "duration",
    },
    {
      title: "Date",
      dataIndex: "date",
      key: "date",
    },
    {
      title: "Primary Emotion",
      dataIndex: "emotion",
      key: "emotion",
    },
  ];

  return (
    <div style={{ padding: "4px" }}>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate("/agents")}
        style={{ marginBottom: "20px" }}
      >
        Back to Agents
      </Button>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <Space>
                <AudioOutlined style={{ fontSize: "24px", color: "#1890ff" }} />
                <Title level={2} style={{ margin: 0 }}>{agent.name}</Title>
              </Space>
              <Paragraph type="secondary" style={{ margin: "4px 0 0 0" }}>
                Integrator Provider: <Tag color="purple">{agent.provider}</Tag> | Total Call Volume: {agent.conversationsCount.toLocaleString()}
              </Paragraph>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <Text strong style={{ fontSize: "16px" }}>Agent Health</Text>
              <Progress
                type="circle"
                percent={agent.healthScore}
                width={50}
                strokeColor={agent.healthScore >= 85 ? "#52c41a" : "#faad14"}
              />
            </div>
          </div>
        </Col>

        {/* METRICS & TRENDS */}
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" title="Average Latency Trend" hoverable>
            <Statistic value={agent.latencyTrend[agent.latencyTrend.length - 1]} suffix=" ms" valueStyle={{ fontWeight: "bold" }} />
            {renderTrendSvg(agent.latencyTrend, "#1890ff", "ms")}
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card size="small" title="Dead Air Ratio Trend" hoverable>
            <Statistic value={agent.deadAirTrend[agent.deadAirTrend.length - 1]} suffix=" %" valueStyle={{ fontWeight: "bold" }} />
            {renderTrendSvg(agent.deadAirTrend, "#faad14", "%")}
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card size="small" title="User Interruptions Trend" hoverable>
            <Statistic value={agent.interruptionsTrend[agent.interruptionsTrend.length - 1]} suffix=" instances" valueStyle={{ fontWeight: "bold" }} />
            {renderTrendSvg(agent.interruptionsTrend, "#ff4d4f", "")}
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card size="small" title="Emotion Score Index" hoverable>
            <Statistic value={agent.emotionTrend[agent.emotionTrend.length - 1]} suffix=" %" valueStyle={{ fontWeight: "bold" }} />
            {renderTrendSvg(agent.emotionTrend, "#52c41a", "%")}
          </Card>
        </Col>

        {/* PROBLEMS & RECENT CALLS */}
        <Col xs={24} md={10}>
          <Card
            title={
              <Space>
                <WarningOutlined style={{ color: "#faad14" }} />
                <span>Top Agent Problems</span>
              </Space>
            }
            style={{ height: "100%" }}
          >
            <List
              dataSource={agent.topProblems}
              renderItem={(item) => (
                <List.Item>
                  <Space align="start">
                    <Tag color="volcano">ALERT</Tag>
                    <Text>{item}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        <Col xs={24} md={14}>
          <Card title="Recent Conversations" style={{ height: "100%" }}>
            <Table
              dataSource={agentConversations}
              columns={columns}
              rowKey="id"
              pagination={false}
              bordered
              size="small"
              locale={{ emptyText: "No recent conversations for this agent." }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

// Activity: simulated update on 2026-04-24

// Activity: simulated update on 2026-06-18
