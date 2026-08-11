import React, { useState, useEffect } from "react";
import { Steps, Card, Form, Input, Button, Table, Select, Typography, Layout, Divider, message } from "antd";
import { API_URL, TOKEN_KEY } from "../../providers/constants";
import { Logo } from "../../components";
import {
  ProjectOutlined,
  UsergroupAddOutlined,
  CheckCircleOutlined,
  PlusOutlined,
  DeleteOutlined,
  ArrowRightOutlined,
  ArrowLeftOutlined
} from "@ant-design/icons";

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

interface Project {
  id: string;
  name: string;
}

interface TeamMember {
  email: string;
  role: string;
}

export const OnboardingPage: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);

  // Step 1 State: Projects
  const [projects, setProjects] = useState<Project[]>([]);
  const [newProjectName, setNewProjectName] = useState("");

  // Step 2 State: Team Members
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [memberForm] = Form.useForm();

  const getHeaders = () => {
    const token = localStorage.getItem(TOKEN_KEY);
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };
  };

  // Fetch initial projects
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const res = await fetch(`${API_URL}/projects`, {
          headers: getHeaders(),
        });
        if (res.ok) {
          const data = await res.json();
          setProjects(data);
        }
      } catch (err) {
        console.error("Failed to load initial projects", err);
      }
    };
    fetchProjects();
  }, []);

  // Step 1 actions: Create Project
  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      message.warning("Please enter a project name");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/projects`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({ name: newProjectName }),
      });
      if (res.ok) {
        const newProj = await res.json();
        setProjects([...projects, { id: newProj.id, name: newProj.name }]);
        setNewProjectName("");
        message.success(`Project "${newProj.name}" created!`);
      } else {
        const errData = await res.json();
        message.error(errData.detail || "Failed to create project");
      }
    } catch (err) {
      message.error("Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  // Step 2 actions: Add coworker to list
  const handleAddCoworker = (values: any) => {
    if (teamMembers.some((m) => m.email === values.email)) {
      message.warning("This email is already in invitation list");
      return;
    }
    setTeamMembers([...teamMembers, { email: values.email, role: values.role }]);
    memberForm.resetFields(["email"]);
  };

  const handleRemoveCoworker = (email: string) => {
    setTeamMembers(teamMembers.filter((m) => m.email !== email));
  };

  // Step 2 actions: Send invites to backend
  const sendTeamInvites = async () => {
    if (teamMembers.length === 0) return true;
    try {
      let allSuccess = true;
      for (const m of teamMembers) {
        const res = await fetch(`${API_URL}/organization/members`, {
          method: "POST",
          headers: getHeaders(),
          body: JSON.stringify({
            email: m.email,
            role: m.role,
          }),
        });
        if (!res.ok) {
          allSuccess = false;
          const errData = await res.json();
          message.error(`Failed to invite ${m.email}: ${errData.detail || "Error"}`);
        }
      }
      return allSuccess;
    } catch (err) {
      message.error("Error occurred while sending invitations");
      return false;
    }
  };

  const handleFinishOnboarding = async () => {
    setLoading(true);
    try {
      // 1. Send coworker invitations
      const invitesSent = await sendTeamInvites();
      if (!invitesSent && teamMembers.length > 0) {
        setLoading(false);
        return; // Don't finalize if we failed to save team invites
      }

      // 2. Mark onboarding as complete in API
      const res = await fetch(`${API_URL}/auth/onboarding/complete`, {
        method: "POST",
        headers: getHeaders(),
      });
      if (res.ok) {
        message.success("Onboarding complete! Welcome to Benten.");
        // Redirect to dashboard with reload to load fresh layouts
        window.location.href = "/dashboard";
      } else {
        const errData = await res.json();
        message.error(errData.detail || "Failed to mark onboarding as completed");
      }
    } catch (err) {
      message.error("Failed to complete onboarding");
    } finally {
      setLoading(false);
    }
  };

  const stepsList = [
    {
      title: "Projects",
      icon: <ProjectOutlined />,
      description: "Set up workspaces",
    },
    {
      title: "Team Members",
      icon: <UsergroupAddOutlined />,
      description: "Invite your coworkers",
    },
  ];

  return (
    <Layout style={{ minHeight: "100vh", display: "flex", justifyContent: "center", alignItems: "center", background: "#f0f2f5", padding: "40px 20px" }}>
      <div style={{ width: "100%", maxWidth: "900px" }}>
        
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <Logo size={46} rounded />
          <Title level={2} style={{ marginTop: "16px" }}>Benten Guided Setup</Title>
          <Paragraph type="secondary" style={{ fontSize: "16px" }}>
            Let's get your workspace completely configured so you can start evaluating voice agents.
          </Paragraph>
        </div>

        <Steps
          current={currentStep}
          items={stepsList}
          style={{ marginBottom: "40px" }}
        />

        {/* STEP 1: Projects */}
        {currentStep === 0 && (
          <Card bordered={false} style={{ boxShadow: "0 4px 12px rgba(0,0,0,0.05)", borderRadius: "12px", padding: "16px" }}>
            <Title level={4}>Create a Project workspace</Title>
            <Paragraph type="secondary">
              Projects align your voice agents, call logs, and performance metrics under distinct categories.
            </Paragraph>

            <div style={{ display: "flex", gap: "12px", marginBottom: "24px" }}>
              <Input
                placeholder="e.g. Sales Agents, Support Bots"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                size="large"
                style={{ maxWidth: "400px" }}
              />
              <Button type="primary" size="large" onClick={handleCreateProject} loading={loading} icon={<PlusOutlined />}>
                Create Project
              </Button>
            </div>

            <Divider />

            {projects.length > 0 && (
              <div style={{ marginBottom: "24px" }}>
                <Title level={5} style={{ marginBottom: "16px" }}>Your Project Workspaces</Title>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {projects.map((project) => (
                    <Card
                      key={project.id}
                      size="small"
                      style={{ borderRadius: "8px", border: "1px solid #e8e8e8", display: "flex", alignItems: "center" }}
                      styles={{ body: { width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px" } }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <ProjectOutlined style={{ fontSize: "18px", color: "#1890ff" }} />
                        <Text strong style={{ fontSize: "15px" }}>{project.name}</Text>
                      </div>
                      <Text type="secondary" style={{ fontSize: "12px" }}>Workspace Ready</Text>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "24px" }}>
              <Button type="primary" size="large" onClick={() => setCurrentStep(1)} disabled={projects.length === 0} icon={<ArrowRightOutlined />}>
                Continue to Team Invites
              </Button>
            </div>
          </Card>
        )}

        {/* STEP 2: Team Members */}
        {currentStep === 1 && (
          <Card bordered={false} style={{ boxShadow: "0 4px 12px rgba(0,0,0,0.05)", borderRadius: "12px", padding: "16px" }}>
            <Title level={4}>Invite Team Members</Title>
            <Paragraph type="secondary">
              Add your coworkers so they can collaborate on checking call metrics and agent dashboards.
            </Paragraph>

            <Form
              form={memberForm}
              layout="vertical"
              onFinish={handleAddCoworker}
              initialValues={{ role: "Viewer" }}
              style={{ maxWidth: "600px", marginBottom: "24px" }}
            >
              <div style={{ display: "flex", gap: "12px", alignItems: "flex-end" }}>
                <Form.Item
                  name="email"
                  label="Coworker Email"
                  rules={[
                    { required: true, message: "Please input email!" },
                    { type: "email", message: "Please input valid email!" }
                  ]}
                  style={{ flex: 1, marginBottom: 0 }}
                >
                  <Input placeholder="coworker@company.com" size="large" />
                </Form.Item>

                <Form.Item
                  name="role"
                  label="Role"
                  style={{ width: "135px", marginBottom: 0 }}
                >
                  <Select size="large">
                    <Option value="Admin">Admin</Option>
                    <Option value="Viewer">Viewer</Option>
                  </Select>
                </Form.Item>

                <Button type="primary" htmlType="submit" size="large" icon={<PlusOutlined />}>
                  Add
                </Button>
              </div>
            </Form>

            <Divider />

            {teamMembers.length > 0 ? (
              <Table
                dataSource={teamMembers}
                rowKey="email"
                pagination={false}
                style={{ marginBottom: "24px" }}
                columns={[
                  {
                    title: "Email",
                    dataIndex: "email",
                    key: "email",
                  },
                  {
                    title: "Workspace Role",
                    dataIndex: "role",
                    key: "role",
                  },
                  {
                    title: "Action",
                    key: "action",
                    render: (_, record) => (
                      <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleRemoveCoworker(record.email)}
                      />
                    ),
                  },
                ]}
              />
            ) : (
              <Paragraph style={{ textAlign: "center", padding: "20px 0" }} type="secondary">
                No invitations added yet. You can invite team members later from organization settings if preferred.
              </Paragraph>
            )}

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "24px" }}>
              <Button size="large" onClick={() => setCurrentStep(0)} icon={<ArrowLeftOutlined />} disabled={loading}>
                Back
              </Button>
              <Button type="primary" size="large" onClick={handleFinishOnboarding} loading={loading} icon={<CheckCircleOutlined />}>
                Finish Setup & Complete
              </Button>
            </div>
          </Card>
        )}

      </div>
    </Layout>
  );
};
