import React from "react";
import { Table, Tag, Button, Typography, Space, Progress, Select } from "antd";
import { AudioOutlined, EyeOutlined, PlusOutlined } from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router";
import { mockAgents, mockProjects } from "../../providers/mockData";

const { Title, Text } = Typography;

export const AgentList: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const projectIdParam = searchParams.get("projectId") || "all";

  const handleProjectFilterChange = (value: string) => {
    if (value === "all") {
      setSearchParams({});
    } else {
      setSearchParams({ projectId: value });
    }
  };

  const filteredAgents = projectIdParam === "all"
    ? mockAgents
    : mockAgents.filter(agent => agent.projectId === projectIdParam);

  const columns = [
    {
      title: "Agent Name",
      dataIndex: "name",
      key: "name",
      render: (text: string) => (
        <Space>
          <AudioOutlined style={{ color: "#1890ff" }} />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: "Project",
      dataIndex: "projectId",
      key: "project",
      render: (projectId: string) => {
        const proj = mockProjects.find(p => p.id === projectId);
        return <Tag color="blue">{proj ? proj.name.split(" ")[0] : projectId}</Tag>;
      },
    },
    {
      title: "Provider",
      dataIndex: "provider",
      key: "provider",
      render: (provider: string) => {
        let color = "purple";
        if (provider === "Vapi") color = "cyan";
        if (provider === "Retell") color = "orange";
        if (provider === "OpenAI Realtime") color = "green";
        return <Tag color={color}>{provider}</Tag>;
      },
    },
    {
      title: "Conversations Count",
      dataIndex: "conversationsCount",
      key: "conversationsCount",
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: "Health Score",
      dataIndex: "healthScore",
      key: "healthScore",
      render: (score: number) => {
        let status = "success";
        if (score < 85) status = "exception";
        return (
          <Space>
            <Progress
              type="circle"
              percent={score}
              width={28}
              strokeColor={score >= 85 ? "#52c41a" : "#faad14"}
              format={() => ""}
            />
            <Text strong style={{ color: score >= 85 ? "#52c41a" : "#faad14" }}>
              {score}%
            </Text>
          </Space>
        );
      },
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: any, record: any) => (
        <Button
          type="primary"
          ghost
          icon={<EyeOutlined />}
          onClick={() => navigate(`/agents/show/${record.id}`)}
        >
          View Details
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: "4px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Voice Agents</Title>
          <Text type="secondary">Monitor configurations, call volumes, and quality indexes of individual AI agents.</Text>
        </div>
        <Space>
          <Select
            value={projectIdParam}
            style={{ width: 220 }}
            onChange={handleProjectFilterChange}
            options={[
              { value: "all", label: "All Projects" },
              ...mockProjects.map(p => ({ value: p.id, label: p.name })),
            ]}
          />
          <Button type="primary" icon={<PlusOutlined />}>Create Agent</Button>
        </Space>
      </div>

      <Table
        dataSource={filteredAgents}
        columns={columns}
        rowKey="id"
        bordered
        pagination={false}
      />
    </div>
  );
};
