import React, { useState } from "react";
import { Row, Col, Card, Statistic, Tag, Button, Typography, Space, Progress, List, Avatar, Input, Form } from "antd";
import { TeamOutlined, PlusOutlined, DatabaseOutlined, KeyOutlined, ProjectOutlined } from "@ant-design/icons";
import { mockMembers, mockOrgStats, Member } from "../../providers/mockData";

const { Title, Text, Paragraph } = Typography;

export const OrganizationList: React.FC = () => {
  const [members, setMembers] = useState<Member[]>(mockMembers);
  const [inviteEmail, setInviteEmail] = useState("");

  const handleInvite = () => {
    if (!inviteEmail) return;
    const newMember: Member = {
      id: `u-${members.length + 1}`,
      name: inviteEmail.split("@")[0],
      email: inviteEmail,
      role: "Viewer",
      avatar: `https://i.pravatar.cc/150?img=${Math.floor(Math.random() * 70)}`,
    };
    setMembers([...members, newMember]);
    setInviteEmail("");
  };

  return (
    <div style={{ padding: "4px" }}>
      <div style={{ marginBottom: "20px" }}>
        <Title level={2} style={{ margin: 0 }}>Organization: {mockOrgStats.name}</Title>
        <Text type="secondary">Manage your organization workspaces, audit access permissions, and track server resource metrics.</Text>
      </div>

      <Row gutter={[16, 16]}>
        {/* STATS ROW */}
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={<Space><TeamOutlined /><span>Total Members</span></Space>}
              value={members.length}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={<Space><ProjectOutlined /><span>Workspaces</span></Space>}
              value={mockOrgStats.projectsCount}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={<Space><KeyOutlined /><span>Active API Keys</span></Space>}
              value={mockOrgStats.apiKeysCount}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Text type="secondary" style={{ fontSize: "12px", display: "block", marginBottom: "4px" }}>
              <DatabaseOutlined /> Storage Consumption
            </Text>
            <Space direction="vertical" style={{ width: "100%" }} size={0}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <Text strong>{mockOrgStats.storageUsedGb} GB</Text>
                <Text type="secondary">Limit: {mockOrgStats.storageLimitGb} GB</Text>
              </div>
              <Progress percent={Math.round((mockOrgStats.storageUsedGb / mockOrgStats.storageLimitGb) * 100)} size="small" status="active" />
            </Space>
          </Card>
        </Col>

        {/* MEMBER LIST */}
        <Col xs={24} md={16}>
          <Card title="Team Members & Roles" extra={<Tag color="blue">Enterprise Plan</Tag>}>
            <List
              itemLayout="horizontal"
              dataSource={members}
              renderItem={(item) => (
                <List.Item
                  actions={[
                    <Button type="link" key="change-role" disabled={item.role === "Owner / Admin"}>Modify Role</Button>,
                    <Button type="link" danger key="remove" disabled={item.role === "Owner / Admin"}>Revoke Access</Button>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<Avatar src={item.avatar} size="large" />}
                    title={<Text strong>{item.name}</Text>}
                    description={
                      <Space>
                        <Text type="secondary" style={{ fontSize: "12px" }}>{item.email}</Text>
                        <Tag color={item.role === "Owner / Admin" ? "gold" : item.role === "Developer" ? "blue" : "default"}>
                          {item.role}
                        </Tag>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* INVITE BOX */}
        <Col xs={24} md={8}>
          <Card title="Invite Team Member" style={{ height: "100%" }}>
            <Paragraph type="secondary" style={{ fontSize: "13px" }}>
              Sent invitations grant default **Viewer** credentials. Role permissions can be changed after acceptance.
            </Paragraph>
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <Input
                placeholder="developer@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
              <Button type="primary" block icon={<PlusOutlined />} onClick={handleInvite}>
                Send Workspace Invite
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

// Activity: simulated update on 2026-04-09

// Activity: simulated update on 2026-04-23

// Activity: simulated update on 2026-04-30

// Activity: simulated update on 2026-06-04
