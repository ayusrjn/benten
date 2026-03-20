import React from "react";
import { Row, Col, Card, Statistic, Tag, Button, Typography, Space, Progress, Badge } from "antd";
import { ProjectOutlined, ArrowRightOutlined, PlusOutlined, CheckCircleOutlined, WarningOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router";
import { mockProjects } from "../../providers/mockData";

const { Title, Text, Paragraph } = Typography;

export const ProjectList: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={{ padding: "4px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Projects</Title>
          <Text type="secondary">Organize your voice agents, alerts, and evaluation sessions into distinct project domains.</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />}>Create Project</Button>
      </div>

      <Row gutter={[16, 16]}>
        {mockProjects.map((project) => {
          const isHealthy = project.avgHealth >= 90;
          return (
            <Col xs={24} md={12} key={project.id}>
              <Card
                hoverable
                actions={[
                  <Button type="link" onClick={() => navigate(`/agents?projectId=${project.id}`)} key="view-agents">
                    View Agents ({project.agentsCount}) <ArrowRightOutlined />
                  </Button>,
                  <Button type="link" key="settings">Configure Settings</Button>,
                ]}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <Space align="start">
                    <ProjectOutlined style={{ fontSize: "28px", color: "#1890ff", marginTop: "4px" }} />
                    <div>
                      <Title level={4} style={{ margin: 0 }}>{project.name}</Title>
                      <Paragraph type="secondary" style={{ margin: "4px 0 12px 0" }}>
                        Voice configuration workspace for regional customer queries and service bots.
                      </Paragraph>
                    </div>
                  </Space>
                  <Badge
                    status={isHealthy ? "success" : "warning"}
                    text={
                      <Tag color={isHealthy ? "success" : "warning"}>
                        {isHealthy ? "Healthy" : "Warning"}
                      </Tag>
                    }
                  />
                </div>

                <Row gutter={16} style={{ marginTop: "12px" }}>
                  <Col span={8}>
                    <Statistic title="Conversations" value={project.conversationsCount} valueStyle={{ fontSize: "18px" }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="Voice Agents" value={project.agentsCount} valueStyle={{ fontSize: "18px" }} />
                  </Col>
                  <Col span={8}>
                    <div style={{ display: "flex", flexDirection: "column" }}>
                      <Text type="secondary" style={{ fontSize: "12px", marginBottom: "4px" }}>Avg Health Score</Text>
                      <Space>
                        <Text strong style={{ fontSize: "18px" }}>{project.avgHealth}%</Text>
                        <Progress
                          type="circle"
                          percent={project.avgHealth}
                          width={24}
                          strokeColor={isHealthy ? "#52c41a" : "#faad14"}
                          showInfo={false}
                        />
                      </Space>
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
};

// Activity: simulated update on 2026-03-20
