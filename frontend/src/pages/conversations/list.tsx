import React, { useState } from "react";
import { Table, Tag, Button, Typography, Space, Input, Select, Slider, Row, Col, Card } from "antd";
import { EyeOutlined, SearchOutlined, FilterOutlined, ClearOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router";
import { mockConversations, mockAgents } from "../../providers/mockData";

const { Title, Text } = Typography;

export const ConversationList: React.FC = () => {
  const navigate = useNavigate();

  // Filters State
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("all");
  const [minScore, setMinScore] = useState(0);
  const [maxLatency, setMaxLatency] = useState(2000);
  const [maxDeadAir, setMaxDeadAir] = useState(100);

  const resetFilters = () => {
    setSearchQuery("");
    setSelectedAgent("all");
    setMinScore(0);
    setMaxLatency(2000);
    setMaxDeadAir(100);
  };

  // Filter Logic
  const filteredConversations = mockConversations.filter((c) => {
    const matchesSearch = c.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          c.agentName.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesAgent = selectedAgent === "all" || c.agentId === selectedAgent;
    const matchesScore = c.score >= minScore;
    const matchesLatency = c.latencyMs <= maxLatency;
    const matchesDeadAir = c.deadAirPercent <= maxDeadAir;

    return matchesSearch && matchesAgent && matchesScore && matchesLatency && matchesDeadAir;
  });

  const columns = [
    {
      title: "Conversation ID",
      dataIndex: "id",
      key: "id",
      render: (text: string) => <Text strong style={{ color: "#1890ff" }}>#{text}</Text>,
    },
    {
      title: "Agent",
      dataIndex: "agentName",
      key: "agentName",
    },
    {
      title: "Date",
      dataIndex: "date",
      key: "date",
    },
    {
      title: "Duration",
      dataIndex: "duration",
      key: "duration",
    },
    {
      title: "Score",
      dataIndex: "score",
      key: "score",
      render: (score: number) => {
        let color = "success";
        if (score < 70) color = "error";
        else if (score < 90) color = "warning";
        return <Tag color={color}>{score} / 100</Tag>;
      },
    },
    {
      title: "Latency",
      dataIndex: "latencyMs",
      key: "latencyMs",
      render: (val: number) => `${val} ms`,
    },
    {
      title: "Dead Air",
      dataIndex: "deadAirPercent",
      key: "deadAirPercent",
      render: (val: number) => `${val}%`,
    },
    {
      title: "Primary Emotion",
      dataIndex: "emotion",
      key: "emotion",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (status: string) => {
        let color = "green";
        if (status === "Warning") color = "orange";
        if (status === "Critical") color = "red";
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: any, record: any) => (
        <Button
          type="primary"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/conversations/show/${record.id}`)}
        >
          Analyze
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: "4px" }}>
      <div style={{ marginBottom: "20px" }}>
        <Title level={2} style={{ margin: 0 }}>Conversations Evaluation Board</Title>
        <Text type="secondary">Investigate specific voice interactions, review timelines, and review detailed audio metrics.</Text>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: "20px" }}>
        {/* Left Side: Filter Sidebar */}
        <Col xs={24} lg={6}>
          <Card title={<Space><FilterOutlined /><span>Filters</span></Space>} extra={<Button type="link" onClick={resetFilters} icon={<ClearOutlined />} style={{ padding: 0 }}>Reset</Button>}>
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <div>
                <Text type="secondary" style={{ display: "block", marginBottom: "4px" }}>Search ID or Agent</Text>
                <Input
                  placeholder="e.g. Sales, A1B2"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  prefix={<SearchOutlined />}
                  allowClear
                />
              </div>

              <div>
                <Text type="secondary" style={{ display: "block", marginBottom: "4px" }}>Agent</Text>
                <Select
                  value={selectedAgent}
                  style={{ width: "100%" }}
                  onChange={(val) => setSelectedAgent(val)}
                  options={[
                    { value: "all", label: "All Agents" },
                    ...mockAgents.map((a) => ({ value: a.id, label: a.name })),
                  ]}
                />
              </div>

              <div>
                <Text type="secondary" style={{ display: "block", marginBottom: "4px" }}>Min Evaluation Score ({minScore})</Text>
                <Slider
                  min={0}
                  max={100}
                  value={minScore}
                  onChange={(val) => setMinScore(val)}
                />
              </div>

              <div>
                <Text type="secondary" style={{ display: "block", marginBottom: "4px" }}>Max Latency Limit ({maxLatency} ms)</Text>
                <Slider
                  min={100}
                  max={2000}
                  step={50}
                  value={maxLatency}
                  onChange={(val) => setMaxLatency(val)}
                />
              </div>

              <div>
                <Text type="secondary" style={{ display: "block", marginBottom: "4px" }}>Max Dead Air Limit ({maxDeadAir}%)</Text>
                <Slider
                  min={0}
                  max={50}
                  value={maxDeadAir}
                  onChange={(val) => setMaxDeadAir(val)}
                />
              </div>
            </Space>
          </Card>
        </Col>

        {/* Right Side: Conversations Table */}
        <Col xs={24} lg={18}>
          <Card style={{ height: "100%" }} bodyStyle={{ padding: "0 0 10px 0" }}>
            <Table
              dataSource={filteredConversations}
              columns={columns}
              rowKey="id"
              bordered
              pagination={{ pageSize: 10 }}
              locale={{ emptyText: "No conversations match the current filter set." }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

// Activity: simulated update on 2026-05-13

// Activity: simulated update on 2026-05-25
