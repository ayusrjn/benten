import React, { useState, useEffect, useContext } from "react";
import { Card, Input, Button, Typography, Layout, Divider, message, Space, Tooltip } from "antd";
import { API_URL, TOKEN_KEY } from "../../providers/constants";
import { Logo } from "../../components";
import { ColorModeContext } from "../../contexts/color-mode";
import {
  ProjectOutlined,
  PlusOutlined,
  ArrowRightOutlined,
  DeleteOutlined,
  SunOutlined,
  MoonOutlined
} from "@ant-design/icons";

const { Title, Text, Paragraph } = Typography;

interface Project {
  id: string;
  name: string;
}

export const OnboardingPage: React.FC = () => {
  const { mode, setMode } = useContext(ColorModeContext);
  const [loading, setLoading] = useState(false);
  const [btnLoading, setBtnLoading] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [newProjectName, setNewProjectName] = useState("");
  const isDark = mode === "dark";

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

  // Create Project
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
        const errData = await res.json().catch(() => ({}));
        message.error(errData.detail || "Failed to create project");
      }
    } catch (err) {
      message.error("Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  // Delete Project
  const handleDeleteProject = async (id: string, name: string) => {
    try {
      const res = await fetch(`${API_URL}/projects/${id}`, {
        method: "DELETE",
        headers: getHeaders(),
      });
      if (res.ok) {
        setProjects(projects.filter((p) => p.id !== id));
        message.success(`Project "${name}" removed`);
      } else {
        const errData = await res.json().catch(() => ({}));
        message.error(errData.detail || "Failed to delete project");
      }
    } catch (err) {
      message.error("Failed to delete project");
    }
  };

  // Finish Onboarding
  const handleFinishOnboarding = async () => {
    if (projects.length === 0) {
      message.error("Please create at least one project workspace to proceed");
      return;
    }
    setBtnLoading(true);
    try {
      const res = await fetch(`${API_URL}/auth/onboarding/complete`, {
        method: "POST",
        headers: getHeaders(),
      });
      if (res.ok) {
        message.success("Setup complete! Welcome to Benten.");
        window.location.href = "/dashboard";
      } else {
        const errData = await res.json().catch(() => ({}));
        message.error(errData.detail || "Failed to mark onboarding as completed");
      }
    } catch (err) {
      message.error("Failed to complete onboarding");
    } finally {
      setBtnLoading(false);
    }
  };

  return (
    <Layout
      style={{
        minHeight: "100vh",
        position: "relative",
        background: isDark
          ? "linear-gradient(135deg, #0e111d 0%, #080a10 50%, #150f28 100%)"
          : "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #e0e7ff 100%)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: "40px 20px",
        overflow: "hidden",
        transition: "background 0.5s ease"
      }}
    >
      {/* Dynamic top bar menu switch */}
      <div style={{ position: "absolute", top: "24px", right: "24px", zIndex: 20 }}>
        <Tooltip title={`Switch to ${isDark ? "Light" : "Dark"} Mode`}>
          <Button
            type="text"
            onClick={() => setMode(isDark ? "light" : "dark")}
            icon={isDark ? <SunOutlined style={{ color: "#faad14" }} /> : <MoonOutlined style={{ color: "#4f46e5" }} />}
            style={{ fontSize: "16px", color: isDark ? "rgba(255,255,255,0.8)" : "#0f172a" }}
          />
        </Tooltip>
      </div>

      {/* Glow Effects */}
      <div
        style={{
          position: "absolute",
          width: "600px",
          height: "600px",
          background: isDark
            ? "radial-gradient(circle, rgba(124, 58, 237, 0.15) 0%, rgba(0,0,0,0) 70%)"
            : "radial-gradient(circle, rgba(165, 180, 252, 0.4) 0%, rgba(0,0,0,0) 70%)",
          top: "-10%",
          left: "-10%",
          borderRadius: "50%",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: "600px",
          height: "600px",
          background: isDark
            ? "radial-gradient(circle, rgba(236, 72, 153, 0.08) 0%, rgba(0,0,0,0) 70%)"
            : "radial-gradient(circle, rgba(251, 207, 232, 0.3) 0%, rgba(0,0,0,0) 70%)",
          bottom: "-10%",
          right: "-10%",
          borderRadius: "50%",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
      />

      <style>{`
        @keyframes fadeUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .onboarding-card {
          animation: fadeUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
          background: ${isDark ? "rgba(255, 255, 255, 0.02)" : "rgba(255, 255, 255, 0.75)"} !important;
          backdrop-filter: blur(20px);
          border: 1px solid ${isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)"} !important;
          box-shadow: ${isDark ? "0 25px 50px -12px rgba(0, 0, 0, 0.5)" : "0 20px 40px -10px rgba(0, 0, 0, 0.05)"} !important;
          border-radius: 20px !important;
          padding: 24px;
        }

        .project-item {
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          background: ${isDark ? "rgba(255, 255, 255, 0.02)" : "rgba(255, 255, 255, 0.9)"} !important;
          border: 1px solid ${isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.05)"} !important;
          border-radius: 12px !important;
        }

        .project-item:hover {
          transform: translateY(-2px);
          background: ${isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(255, 255, 255, 0.98)"} !important;
          border-color: rgba(124, 58, 237, 0.3) !important;
          box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
        }

        .custom-input {
          background: ${isDark ? "rgba(255, 255, 255, 0.03)" : "rgba(0, 0, 0, 0.01)"} !important;
          border: 1px solid ${isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.12)"} !important;
          color: ${isDark ? "#fff" : "#0f172a"} !important;
          transition: all 0.3s ease !important;
        }

        .custom-input:focus {
          border-color: #7c3aed !important;
          box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.2) !important;
          background: ${isDark ? "rgba(255, 255, 255, 0.05)" : "#fff"} !important;
        }

        .custom-input::placeholder {
          color: ${isDark ? "rgba(255, 255, 255, 0.35)" : "rgba(15, 23, 42, 0.4)"} !important;
        }

        .gradient-btn {
          background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%) !important;
          border: none !important;
          color: white !important;
          transition: all 0.3s ease !important;
        }

        .gradient-btn:hover:not(:disabled) {
          filter: brightness(1.1);
          box-shadow: 0 0 15px rgba(124, 58, 237, 0.4) !important;
          transform: translateY(-1px);
        }

        .gradient-btn:disabled {
          background: ${isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(0, 0, 0, 0.04)"} !important;
          color: ${isDark ? "rgba(255, 255, 255, 0.25)" : "rgba(0, 0, 0, 0.3)"} !important;
          border: 1px solid ${isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.05)"} !important;
        }

        .action-icon {
          color: ${isDark ? "rgba(255, 255, 255, 0.4)" : "rgba(0, 0, 0, 0.4)"};
          transition: color 0.2s ease;
        }

        .action-icon:hover {
          color: #ff4d4f;
        }
      `}</style>

      <div style={{ width: "100%", maxWidth: "680px", zIndex: 10 }}>
        
        {/* Title Header */}
        <div style={{ textAlign: "center", marginBottom: "32px", animation: "fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards" }}>
          <Logo size={52} rounded />
          <Title
            level={2}
            style={{
              marginTop: "20px",
              marginBottom: "8px",
              background: isDark
                ? "linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%)"
                : "linear-gradient(135deg, #53457a 0%, #1e1b4b 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              fontWeight: 700,
              letterSpacing: "-0.5px"
            }}
          >
            Create Your Workspace
          </Title>
          <Paragraph style={{ color: isDark ? "rgba(255, 255, 255, 0.45)" : "#5c6f84", fontSize: "15px", margin: 0 }}>
            Projects organize your voice agents, call analytics, and incident reports under separate spaces. Create at least one project to get started.
          </Paragraph>
        </div>

        {/* Setup card */}
        <Card bordered={false} className="onboarding-card">
          <Title level={4} style={{ color: isDark ? "#fff" : "#0f172a", marginBottom: "4px", fontSize: "17px", fontWeight: 600 }}>
            Project Workspaces
          </Title>
          <Paragraph style={{ color: isDark ? "rgba(255, 255, 255, 0.4)" : "#6b7280", fontSize: "13px", marginBottom: "20px" }}>
            Add workspaces matching your business use-cases (e.g. "Customer Support Bots", "Sales Agents").
          </Paragraph>

          {/* Form Area */}
          <div style={{ display: "flex", gap: "12px", marginBottom: "28px" }}>
            <Input
              placeholder="e.g. Support & QA Agents"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              onPressEnter={handleCreateProject}
              size="large"
              className="custom-input"
              style={{ flex: 1, borderRadius: "10px" }}
              disabled={loading}
            />
            <Button
              type="primary"
              size="large"
              onClick={handleCreateProject}
              loading={loading}
              icon={<PlusOutlined />}
              style={{
                borderRadius: "10px",
                height: "40px",
                background: "#7c3aed",
                borderColor: "#7c3aed",
                fontWeight: 500
              }}
            >
              Create
            </Button>
          </div>

          {/* Project List */}
          {projects.length > 0 && (
            <div style={{ marginBottom: "28px" }}>
              <Divider style={{ borderColor: isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.08)", margin: "0 0 20px 0" }} />
              <Title level={5} style={{ color: isDark ? "rgba(255, 255, 255, 0.6)" : "#65597a", fontSize: "13px", fontWeight: 600, letterSpacing: "0.5px", textTransform: "uppercase", marginBottom: "12px" }}>
                Active Workspaces ({projects.length})
              </Title>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {projects.map((project) => (
                  <Card
                    key={project.id}
                    size="small"
                    className="project-item"
                    styles={{ body: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 16px" } }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <ProjectOutlined style={{ fontSize: "18px", color: "#a78bfa" }} />
                      <Text style={{ color: isDark ? "#fff" : "#0f172a", fontSize: "14px", fontWeight: 500 }}>
                        {project.name}
                      </Text>
                    </div>
                    
                    <Space size={16}>
                      <span style={{ fontSize: "11px", color: isDark ? "rgba(255, 255, 255, 0.35)" : "rgba(0, 0, 0, 0.35)", fontWeight: 500 }}>
                        Ready
                      </span>
                      <Tooltip title="Delete Workspace">
                        <Button
                          type="text"
                          icon={<DeleteOutlined className="action-icon" />}
                          onClick={() => handleDeleteProject(project.id, project.name)}
                          style={{ padding: 4, height: "auto" }}
                        />
                      </Tooltip>
                    </Space>
                  </Card>
                ))}
              </div>
            </div>
          )}

          <Divider style={{ borderColor: isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.08)", margin: "24px 0" }} />

          {/* Finish Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <Button
              type="primary"
              size="large"
              onClick={handleFinishOnboarding}
              loading={btnLoading}
              disabled={projects.length === 0}
              className="gradient-btn"
              style={{
                borderRadius: "10px",
                height: "44px",
                padding: "0 28px",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "8px"
              }}
            >
              Start Evaluating Agents <ArrowRightOutlined />
            </Button>
          </div>
        </Card>

      </div>
    </Layout>
  );
};
