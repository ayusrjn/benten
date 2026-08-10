import React, { useEffect, useState } from "react";
import {
  Card,
  Row,
  Col,
  Typography,
  Tag,
  Button,
  Input,
  Segmented,
  Space,
  Badge,
  Spin,
  Drawer,
  Empty,
  Statistic,
  Tooltip,
  Divider,
  Progress,
  Tabs,
  notification,
} from "antd";
import {
  RobotOutlined,
  SyncOutlined,
  SearchOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  MessageOutlined,
  ThunderboltOutlined,
  RightOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router";
import { API_URL, TOKEN_KEY } from "../../providers/constants";

const { Title, Text, Paragraph } = Typography;

export interface AgentItem {
  id: string;
  projectId: string;
  name: string;
  provider: string;
  externalId?: string;
  description?: string;
  lastSyncedAt?: string;
  rawMetadata?: any;
  conversationsCount: number;
  healthScore: number;
  latencyTrend: number[];
  deadAirTrend: number[];
  interruptionsTrend: number[];
  emotionTrend: number[];
  topProblems: string[];
}

const PROVIDER_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  elevenlabs: { bg: "#f3e8ff", text: "#7e22ce", border: "#d8b4fe" },
  vapi: { bg: "#e0f2fe", text: "#0369a1", border: "#bae6fd" },
  retell: { bg: "#ecfdf5", text: "#047857", border: "#a7f3d0" },
  bolna: { bg: "#e0f2fe", text: "#0284c7", border: "#bae6fd" },
  default: { bg: "#f3f4f6", text: "#374151", border: "#e5e7eb" },
};

export const AgentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedProvider, setSelectedProvider] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [syncingGlobal, setSyncingGlobal] = useState<boolean>(false);
  const [syncingProvider, setSyncingProvider] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentItem | null>(null);
  const [drawerVisible, setDrawerVisible] = useState<boolean>(false);

  const fetchAgents = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      const res = await fetch(`${API_URL}/agents`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        throw new Error("Failed to fetch agents list");
      }

      const data = await res.json();
      setAgents(data || []);
    } catch (err: any) {
      console.error(err);
      notification.error({
        message: "Error Loading Agents",
        description: err.message || "Failed to load voice agents.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  // Filter agents based on provider and search query
  const filteredAgents = agents.filter((agent) => {
    const matchesProvider =
      selectedProvider === "all" ||
      agent.provider.toLowerCase() === selectedProvider.toLowerCase();
    const matchesSearch =
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (agent.externalId &&
        agent.externalId.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (agent.description &&
        agent.description.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesProvider && matchesSearch;
  });

  // Calculate summary metrics
  const totalAgents = agents.length;
  const ratedAgents = agents.filter((a) => a.conversationsCount > 0);
  const healthyAgentsCount = ratedAgents.filter((a) => a.healthScore >= 80).length;
  const totalConversations = agents.reduce((acc, a) => acc + a.conversationsCount, 0);
  const avgHealthScore =
    ratedAgents.length > 0
      ? Math.round(ratedAgents.reduce((acc, a) => acc + a.healthScore, 0) / ratedAgents.length)
      : 0;

  // Handle global sync
  const handleGlobalSync = async () => {
    setSyncingGlobal(true);
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      const res = await fetch(`${API_URL}/agents/sync`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to sync agents");
      }

      const json = await res.json();
      if (json.success) {
        notification.success({
          message: "Agents Synchronized",
          description: json.message || `Successfully synced ${json.totalSynced} agents`,
        });
      } else {
        notification.warning({
          message: "Sync Notice",
          description: json.message || "No connected provider integrations found.",
        });
      }
      await fetchAgents();
    } catch (err: any) {
      console.error(err);
      notification.error({
        message: "Sync Failed",
        description: err.message || "An error occurred during synchronization",
      });
    } finally {
      setSyncingGlobal(false);
    }
  };

  // Handle provider specific sync
  const handleProviderSync = async (providerKey: string) => {
    setSyncingProvider(providerKey);
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      const res = await fetch(`${API_URL}/integrations/${providerKey}/sync-agents`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Failed to sync ${providerKey} agents`);
      }

      const json = await res.json();
      notification.success({
        message: `${providerKey.toUpperCase()} Sync Complete`,
        description: json.message,
      });
      await fetchAgents();
    } catch (err: any) {
      console.error(err);
      notification.error({
        message: "Sync Failed",
        description: err.message || "Could not sync provider agents",
      });
    } finally {
      setSyncingProvider(null);
    }
  };

  return (
    <div style={{ padding: "24px", maxWidth: "1400px", margin: "0 auto" }}>
      {/* Header Banner */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
          marginBottom: "24px",
          background: "linear-gradient(135deg, #001529 0%, #003a8c 100%)",
          padding: "24px 32px",
          borderRadius: "12px",
          color: "#ffffff",
          boxShadow: "0 10px 25px -5px rgba(0, 58, 140, 0.3)",
        }}
      >
        <div>
          <Space align="center" size={12}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 10,
                background: "rgba(255, 255, 255, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 24,
              }}
            >
              <RobotOutlined />
            </div>
            <div>
              <Title level={3} style={{ color: "#fff", margin: 0 }}>
                Voice AI Agents
              </Title>
              <Text style={{ color: "rgba(255, 255, 255, 0.75)" }}>
                Discovered and normalized voice agents across ElevenLabs, Vapi, and Retell connectors
              </Text>
            </div>
          </Space>
        </div>

        <Space size={12}>
          <Button
            type="primary"
            icon={<SyncOutlined spin={syncingGlobal} />}
            loading={syncingGlobal}
            onClick={handleGlobalSync}
            style={{
              height: "40px",
              borderRadius: "8px",
              background: "#1890ff",
              borderColor: "#1890ff",
              fontWeight: 600,
            }}
          >
            Sync All Agents
          </Button>
          <Button
            icon={<ApiOutlined />}
            onClick={() => navigate("/integrations")}
            style={{
              height: "40px",
              borderRadius: "8px",
              background: "rgba(255, 255, 255, 0.15)",
              borderColor: "rgba(255, 255, 255, 0.3)",
              color: "#fff",
            }}
          >
            Integrations Settings
          </Button>
        </Space>
      </div>

      {/* Summary Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card
            bordered={false}
            style={{
              borderRadius: "12px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
              background: "#ffffff",
            }}
          >
            <Statistic
              title={<Text type="secondary">Total Active Agents</Text>}
              value={totalAgents}
              prefix={<RobotOutlined style={{ color: "#1890ff", marginRight: 8 }} />}
              valueStyle={{ fontWeight: 700, color: "#1f2937" }}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Normalized across connected APIs
              </Text>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card
            bordered={false}
            style={{
              borderRadius: "12px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
              background: "#ffffff",
            }}
          >
            <Statistic
              title={<Text type="secondary">Healthy Agents (&ge;80%)</Text>}
              value={healthyAgentsCount}
              suffix={`/ ${totalAgents}`}
              prefix={<CheckCircleOutlined style={{ color: "#52c41a", marginRight: 8 }} />}
              valueStyle={{ fontWeight: 700, color: "#52c41a" }}
            />
            <div style={{ marginTop: 8 }}>
              <Progress
                percent={totalAgents > 0 ? Math.round((healthyAgentsCount / totalAgents) * 100) : 100}
                size="small"
                status="active"
                strokeColor="#52c41a"
              />
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card
            bordered={false}
            style={{
              borderRadius: "12px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
              background: "#ffffff",
            }}
          >
            <Statistic
              title={<Text type="secondary">Average Platform Health</Text>}
              value={avgHealthScore}
              suffix="/ 100"
              prefix={<ThunderboltOutlined style={{ color: "#faad14", marginRight: 8 }} />}
              valueStyle={{ fontWeight: 700, color: avgHealthScore >= 80 ? "#52c41a" : "#faad14" }}
            />
            <div style={{ marginTop: 8 }}>
              <Progress
                percent={avgHealthScore}
                size="small"
                showInfo={false}
                strokeColor={avgHealthScore >= 80 ? "#52c41a" : "#faad14"}
              />
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card
            bordered={false}
            style={{
              borderRadius: "12px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
              background: "#ffffff",
            }}
          >
            <Statistic
              title={<Text type="secondary">Evaluated Call Sessions</Text>}
              value={totalConversations}
              prefix={<MessageOutlined style={{ color: "#722ed1", marginRight: 8 }} />}
              valueStyle={{ fontWeight: 700, color: "#722ed1" }}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Mapped turn segments &amp; audio metrics
              </Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Filter and Search Bar */}
      <Card
        bordered={false}
        style={{
          borderRadius: "12px",
          marginBottom: "24px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
        }}
      >
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Space direction="vertical" style={{ width: "100%" }}>
              <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>
                FILTER BY PROVIDER CONNECTOR
              </Text>
              <Segmented
                options={[
                  { label: `All Agents (${totalAgents})`, value: "all" },
                  {
                    label: `ElevenLabs (${agents.filter((a) => a.provider.toLowerCase() === "elevenlabs").length})`,
                    value: "elevenlabs",
                  },
                  {
                    label: `Vapi (${agents.filter((a) => a.provider.toLowerCase() === "vapi").length})`,
                    value: "vapi",
                  },
                  {
                    label: `Retell (${agents.filter((a) => a.provider.toLowerCase() === "retell").length})`,
                    value: "retell",
                  },
                  {
                    label: `Bolna (${agents.filter((a) => a.provider.toLowerCase() === "bolna").length})`,
                    value: "bolna",
                  },
                ]}
                value={selectedProvider}
                onChange={(val) => setSelectedProvider(val as string)}
                style={{ background: "#f3f4f6", padding: 4 }}
              />
            </Space>
          </Col>

          <Col xs={24} md={10}>
            <Space direction="vertical" style={{ width: "100%" }}>
              <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>
                SEARCH AGENT OR EXTERNAL ID
              </Text>
              <Input
                placeholder="Search by agent name, ID, or tags..."
                prefix={<SearchOutlined style={{ color: "#bfbfbf" }} />}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                allowClear
                style={{ borderRadius: "8px", height: "38px" }}
              />
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Main Grid View */}
      {isLoading ? (
        <div style={{ textAlign: "center", padding: "60px 0" }}>
          <Spin size="large" tip="Loading discovered agents..." />
        </div>
      ) : filteredAgents.length === 0 ? (
        <Card style={{ borderRadius: "12px", textAlign: "center", padding: "40px" }}>
          <Empty
            description={
              <div>
                <Title level={5}>No Agents Discovered</Title>
                <Text type="secondary">
                  {searchQuery || selectedProvider !== "all"
                    ? "No agents match the current filter or search criteria."
                    : "Connect an API key (e.g. 'mock' or your provider key) under Settings/Integrations and click Save Settings."}
                </Text>
              </div>
            }
          >
            <Space size={12} style={{ marginTop: 16 }}>
              <Button
                type="primary"
                icon={<ApiOutlined />}
                onClick={() => navigate("/integrations")}
              >
                Go to Integrations
              </Button>
              <Button
                icon={<SyncOutlined />}
                onClick={handleGlobalSync}
                loading={syncingGlobal}
              >
                Sync All Agents
              </Button>
            </Space>
          </Empty>
        </Card>
      ) : (
        <Row gutter={[20, 20]}>
          {filteredAgents.map((agent) => {
            const providerKey = agent.provider.toLowerCase();
            const colors = PROVIDER_COLORS[providerKey] || PROVIDER_COLORS.default;
            const hasCalls = agent.conversationsCount > 0 && agent.latencyTrend && agent.latencyTrend.length > 0;
            const latestLatency = hasCalls ? `${agent.latencyTrend[agent.latencyTrend.length - 1]}ms` : "N/A";
            const latestDeadAir = hasCalls ? `${agent.deadAirTrend[agent.deadAirTrend.length - 1]}%` : "N/A";

            return (
              <Col xs={24} sm={12} lg={8} key={agent.id}>
                <Card
                  hoverable
                  style={{
                    borderRadius: "12px",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
                    border: "1px solid #f0f0f0",
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                  }}
                  bodyStyle={{ flex: 1, padding: "20px", display: "flex", flexDirection: "column" }}
                >
                  {/* Top Bar: Provider Tag + Health Score */}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "14px",
                    }}
                  >
                    <Tag
                      style={{
                        background: colors.bg,
                        color: colors.text,
                        borderColor: colors.border,
                        borderRadius: "6px",
                        padding: "2px 10px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        fontSize: 11,
                      }}
                    >
                      {agent.provider}
                    </Tag>

                    <Space size={6}>
                      <Badge
                        status={
                          !hasCalls
                            ? "default"
                            : agent.healthScore >= 80
                              ? "success"
                              : agent.healthScore >= 60
                                ? "warning"
                                : "error"
                        }
                      />
                      <Text
                        strong
                        style={{
                          color: !hasCalls
                            ? "#8c8c8c"
                            : agent.healthScore >= 80
                              ? "#52c41a"
                              : agent.healthScore >= 60
                                ? "#faad14"
                                : "#ff4d4f",
                        }}
                      >
                        {hasCalls ? `${agent.healthScore} Score` : "Unrated"}
                      </Text>
                    </Space>
                  </div>

                  {/* Agent Title & Description */}
                  <div style={{ marginBottom: "16px" }}>
                    <Title level={4} style={{ margin: "0 0 4px 0", fontSize: 17, color: "#111827" }}>
                      {agent.name}
                    </Title>

                    {agent.externalId && (
                      <Text
                        type="secondary"
                        copyable
                        style={{ fontSize: 12, fontFamily: "monospace", display: "block", marginBottom: 6 }}
                      >
                        ID: {agent.externalId}
                      </Text>
                    )}

                    {agent.description ? (
                      <Paragraph
                        type="secondary"
                        ellipsis={{ rows: 2 }}
                        style={{ fontSize: 13, margin: 0, minHeight: 38 }}
                      >
                        {agent.description}
                      </Paragraph>
                    ) : (
                      <Text type="secondary" style={{ fontSize: 13, fontStyle: "italic" }}>
                        No description provided by connector.
                      </Text>
                    )}
                  </div>

                  <Divider style={{ margin: "12px 0" }} />

                  {/* Metrics Row */}
                  <Row gutter={12} style={{ marginBottom: "16px" }}>
                    <Col span={8}>
                      <div
                        style={{
                          background: "#f9fafb",
                          padding: "8px 10px",
                          borderRadius: "8px",
                          textAlign: "center",
                        }}
                      >
                        <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
                          Calls
                        </Text>
                        <Text strong style={{ fontSize: 15, color: "#1f2937" }}>
                          {agent.conversationsCount}
                        </Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div
                        style={{
                          background: "#f9fafb",
                          padding: "8px 10px",
                          borderRadius: "8px",
                          textAlign: "center",
                        }}
                      >
                        <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
                          Avg Latency
                        </Text>
                        <Text strong style={{ fontSize: 15, color: hasCalls ? "#1890ff" : "#8c8c8c" }}>
                          {latestLatency}
                        </Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div
                        style={{
                          background: "#f9fafb",
                          padding: "8px 10px",
                          borderRadius: "8px",
                          textAlign: "center",
                        }}
                      >
                        <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
                          Dead Air
                        </Text>
                        <Text strong style={{ fontSize: 15, color: hasCalls ? "#faad14" : "#8c8c8c" }}>
                          {latestDeadAir}
                        </Text>
                      </div>
                    </Col>
                  </Row>

                  {/* Top Problems / Flags */}
                  <div style={{ flex: 1, marginBottom: "16px" }}>
                    <Text type="secondary" style={{ fontSize: 11, fontWeight: 600, display: "block", marginBottom: 6 }}>
                      DETECTED INCIDENT FLAGS
                    </Text>
                    {!hasCalls ? (
                      <Text type="secondary" style={{ fontSize: 12, fontStyle: "italic" }}>
                        Pending call evaluation
                      </Text>
                    ) : agent.topProblems && agent.topProblems.length > 0 ? (
                      <Space direction="vertical" size={4} style={{ width: "100%" }}>
                        {agent.topProblems.slice(0, 2).map((prob, idx) => (
                          <Tag
                            key={idx}
                            color="volcano"
                            style={{
                              borderRadius: "4px",
                              fontSize: 11,
                              whiteSpace: "normal",
                              wordBreak: "break-word",
                            }}
                          >
                            <ExclamationCircleOutlined style={{ marginRight: 4 }} />
                            {prob}
                          </Tag>
                        ))}
                      </Space>
                    ) : (
                      <Tag color="green" style={{ borderRadius: "4px", fontSize: 11 }}>
                        <CheckCircleOutlined style={{ marginRight: 4 }} />
                        No Critical Anomalies
                      </Tag>
                    )}
                  </div>

                  {/* Card Footer Actions */}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      paddingTop: "12px",
                      borderTop: "1px solid #f0f0f0",
                    }}
                  >
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      <ClockCircleOutlined style={{ marginRight: 4 }} />
                      {agent.lastSyncedAt
                        ? `Synced ${new Date(agent.lastSyncedAt).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}`
                        : "Synced"}
                    </Text>

                    <Space size={8}>
                      <Tooltip title={`Re-sync ${agent.provider} connector`}>
                        <Button
                          size="small"
                          icon={<SyncOutlined spin={syncingProvider === providerKey} />}
                          onClick={() => handleProviderSync(providerKey)}
                        />
                      </Tooltip>
                      <Button
                        size="small"
                        type="primary"
                        ghost
                        icon={<RightOutlined />}
                        onClick={() => {
                          setSelectedAgent(agent);
                          setDrawerVisible(true);
                        }}
                      >
                        Details
                      </Button>
                    </Space>
                  </div>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}

      {/* Agent Detail Drawer */}
      <Drawer
        title={
          selectedAgent ? (
            <Space align="center">
              <RobotOutlined style={{ color: "#1890ff", fontSize: 20 }} />
              <div>
                <Text strong style={{ fontSize: 16, display: "block" }}>
                  {selectedAgent.name}
                </Text>
                <Tag style={{ fontSize: 10, textTransform: "uppercase" }}>
                  {selectedAgent.provider}
                </Tag>
              </div>
            </Space>
          ) : (
            "Agent Details"
          )
        }
        placement="right"
        width={600}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedAgent && (
          <div>
            <Tabs
              defaultActiveKey="overview"
              items={[
                {
                  key: "overview",
                  label: "Overview & Analytics",
                  children: (
                    <Space direction="vertical" size={16} style={{ width: "100%" }}>
                      <Card size="small" style={{ background: "#fafafa", borderRadius: 8 }}>
                        <Title level={5} style={{ margin: "0 0 8px 0" }}>
                          Internal Metadata
                        </Title>
                        <Row gutter={[12, 12]}>
                          <Col span={12}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              Provider:
                            </Text>
                            <Text strong style={{ display: "block" }}>
                              {selectedAgent.provider.toUpperCase()}
                            </Text>
                          </Col>
                          <Col span={12}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              External ID:
                            </Text>
                            <Text copyable style={{ display: "block", fontFamily: "monospace" }}>
                              {selectedAgent.externalId || "N/A"}
                            </Text>
                          </Col>
                          <Col span={24}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              Description:
                            </Text>
                            <Text style={{ display: "block" }}>
                              {selectedAgent.description || "No description available"}
                            </Text>
                          </Col>
                        </Row>
                      </Card>

                      <Card size="small" title="Call Health & Latency Performance">
                        <Row gutter={[16, 16]}>
                          <Col span={12}>
                            <Statistic
                              title="Health Score"
                              value={selectedAgent.conversationsCount > 0 ? selectedAgent.healthScore : "Unrated"}
                              suffix={selectedAgent.conversationsCount > 0 ? "/ 100" : ""}
                              valueStyle={{
                                color:
                                  selectedAgent.conversationsCount === 0
                                    ? "#8c8c8c"
                                    : selectedAgent.healthScore >= 80
                                      ? "#52c41a"
                                      : "#faad14",
                              }}
                            />
                          </Col>
                          <Col span={12}>
                            <Statistic
                              title="Total Conversations"
                              value={selectedAgent.conversationsCount}
                            />
                          </Col>
                        </Row>
                      </Card>

                      <Card size="small" title="Detected Quality Bottlenecks">
                        {selectedAgent.conversationsCount === 0 ? (
                          <Text type="secondary" style={{ fontSize: 13, fontStyle: "italic" }}>
                            No call recordings evaluated yet for this agent.
                          </Text>
                        ) : selectedAgent.topProblems && selectedAgent.topProblems.length > 0 ? (
                          <Space direction="vertical" style={{ width: "100%" }}>
                            {selectedAgent.topProblems.map((prob, i) => (
                              <Tag key={i} color="volcano" style={{ padding: "4px 8px" }}>
                                <ExclamationCircleOutlined style={{ marginRight: 6 }} />
                                {prob}
                              </Tag>
                            ))}
                          </Space>
                        ) : (
                          <Tag color="green" style={{ padding: "4px 8px" }}>
                            <CheckCircleOutlined style={{ marginRight: 6 }} />
                            No Critical Anomalies Detected
                          </Tag>
                        )}
                      </Card>
                    </Space>
                  ),
                },
                {
                  key: "raw",
                  label: "Raw Connector JSON",
                  children: (
                    <div>
                      <Paragraph type="secondary" style={{ fontSize: 12 }}>
                        Provider response JSON payload received during connector synchronization:
                      </Paragraph>
                      <pre
                        style={{
                          background: "#1e1e1e",
                          color: "#9cdcfe",
                          padding: "16px",
                          borderRadius: "8px",
                          fontSize: "12px",
                          overflowX: "auto",
                          maxHeight: "450px",
                        }}
                      >
                        {JSON.stringify(selectedAgent.rawMetadata || {}, null, 2)}
                      </pre>
                    </div>
                  ),
                },
              ]}
            />
          </div>
        )}
      </Drawer>
    </div>
  );
};
