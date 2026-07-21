import React, { useEffect, useState } from "react";
import {
  Table,
  Card,
  Tag,
  Input,
  Select,
  Button,
  Space,
  Typography,
  Tooltip,
  Badge,
  Skeleton,
  Empty,
  Alert,
  notification,
  theme
} from "antd";
import {
  SearchOutlined,
  SyncOutlined,
  CloudDownloadOutlined,
  RightOutlined,
  SoundOutlined,
  FileTextOutlined,
  ApiOutlined,
  ReloadOutlined,
  FilterOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined
} from "@ant-design/icons";
import { useNavigate } from "react-router";
import { API_URL, TOKEN_KEY } from "../../providers/constants";
import { CallDetailDrawer, CallDetail } from "./detail-drawer";

const { Title, Text } = Typography;
const { Option } = Select;

const PROVIDER_COLORS: Record<string, string> = {
  vapi: "#8b5cf6",
  retell: "#10b981",
  elevenlabs: "#f59e0b"
};

export const CallsPage: React.FC = () => {
  const { token } = theme.useToken();
  const navigate = useNavigate();

  const [calls, setCalls] = useState<CallDetail[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [providerFilter, setProviderFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [gradeFilter, setGradeFilter] = useState<string>("all");
  const [durationFilter, setDurationFilter] = useState<string>("all");
  const [agentFilter, setAgentFilter] = useState<string>("all");

  // Agents dropdown list
  const [agentsList, setAgentsList] = useState<any[]>([]);

  // Drawer state
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [selectedCall, setSelectedCall] = useState<CallDetail | null>(null);
  const [drawerLoading, setDrawerLoading] = useState<boolean>(false);
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);

  // Syncing state
  const [syncing, setSyncing] = useState<boolean>(false);

  // Pagination state
  const [pagination, setPagination] = useState({ current: 1, pageSize: 25, total: 0 });

  const fetchCalls = async () => {
    setLoading(true);
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const params = new URLSearchParams();

      if (searchQuery) params.append("q", searchQuery);
      if (providerFilter !== "all") params.append("provider", providerFilter);
      if (statusFilter !== "all") params.append("status", statusFilter);
      if (gradeFilter !== "all") params.append("grade", gradeFilter);
      if (agentFilter !== "all") params.append("agentId", agentFilter);

      // Duration ranges
      if (durationFilter === "lt30") {
        params.append("maxDuration", "30");
      } else if (durationFilter === "30to120") {
        params.append("minDuration", "30");
        params.append("maxDuration", "120");
      } else if (durationFilter === "2mto5m") {
        params.append("minDuration", "120");
        params.append("maxDuration", "300");
      } else if (durationFilter === "gt5m") {
        params.append("minDuration", "300");
      }

      // Pagination calculation
      const start = (pagination.current - 1) * pagination.pageSize;
      const end = start + pagination.pageSize;
      params.append("_start", start.toString());
      params.append("_end", end.toString());
      params.append("_sort", "date");
      params.append("_order", "desc");

      const response = await fetch(`${API_URL}/conversations?${params.toString()}`, {
        headers: { Authorization: `Bearer ${tokenVal}` }
      });

      if (!response.ok) throw new Error("Failed to fetch calls");

      const data = await response.json();
      const totalCount = parseInt(response.headers.get("x-total-count") || "0", 10);

      setCalls(data);
      setPagination(prev => ({ ...prev, total: totalCount }));
      setError(null);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load calls.");
    } finally {
      setLoading(false);
    }
  };

  const fetchAgents = async () => {
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const res = await fetch(`${API_URL}/agents`, {
        headers: { Authorization: `Bearer ${tokenVal}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAgentsList(data);
      }
    } catch (err) {
      console.error("Failed to load agents list", err);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  useEffect(() => {
    fetchCalls();
  }, [searchQuery, providerFilter, statusFilter, gradeFilter, durationFilter, agentFilter, pagination.current, pagination.pageSize]);

  const handleSyncAllCalls = async () => {
    setSyncing(true);
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const providers = ["vapi", "retell", "elevenlabs"];
      let totalImported = 0;

      for (const prov of providers) {
        const res = await fetch(`${API_URL}/integrations/${prov}/sync-calls`, {
          method: "POST",
          headers: { Authorization: `Bearer ${tokenVal}` }
        });
        if (res.ok) {
          const data = await res.json();
          totalImported += data.imported || 0;
        }
      }

      notification.success({
        message: "Call Sync Completed",
        description: `Successfully synchronized providers. Imported ${totalImported} new calls.`,
        placement: "bottomRight"
      });

      fetchCalls();
    } catch (err: any) {
      notification.error({
        message: "Sync Failed",
        description: err.message || "Failed to trigger call synchronization",
        placement: "bottomRight"
      });
    } finally {
      setSyncing(false);
    }
  };

  const handleOpenCallDetail = async (callId: string) => {
    setSelectedCallId(callId);
    setDrawerOpen(true);
    setDrawerLoading(true);
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const res = await fetch(`${API_URL}/conversations/${callId}`, {
        headers: { Authorization: `Bearer ${tokenVal}` }
      });
      if (!res.ok) throw new Error("Failed to fetch call details");
      const data = await res.json();
      setSelectedCall(data);
    } catch (err: any) {
      notification.error({
        message: "Error Loading Call",
        description: err.message || "Could not retrieve call details.",
        placement: "bottomRight"
      });
    } finally {
      setDrawerLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return token.colorSuccess;
    if (score >= 70) return token.colorWarning;
    return token.colorError;
  };

  // Compute summary KPI metrics from current calls
  const evaluatedCalls = calls.filter(c => c.score !== null && c.score !== undefined);
  const avgHealth = evaluatedCalls.length > 0
    ? Math.round(evaluatedCalls.reduce((acc, c) => acc + (c.score || 0), 0) / evaluatedCalls.length)
    : null;
  
  const evaluatedMos = calls.filter(c => c.rawMetrics?.mos_score !== undefined && c.rawMetrics?.mos_score !== null);
  const avgMos = evaluatedMos.length > 0
    ? (evaluatedMos.reduce((acc, c) => acc + (c.rawMetrics.mos_score || 0), 0) / evaluatedMos.length).toFixed(2)
    : null;

  const evaluatedLatency = calls.filter(c => c.latencyMs !== null && c.latencyMs !== undefined);
  const avgLatency = evaluatedLatency.length > 0
    ? Math.round(evaluatedLatency.reduce((acc, c) => acc + (c.latencyMs || 0), 0) / evaluatedLatency.length)
    : null;

  const activeFilterCount = (providerFilter !== "all" ? 1 : 0) +
    (statusFilter !== "all" ? 1 : 0) +
    (gradeFilter !== "all" ? 1 : 0) +
    (durationFilter !== "all" ? 1 : 0) +
    (agentFilter !== "all" ? 1 : 0);

  const resetFilters = () => {
    setSearchQuery("");
    setProviderFilter("all");
    setStatusFilter("all");
    setGradeFilter("all");
    setDurationFilter("all");
    setAgentFilter("all");
  };

  // Streamlined, uncluttered column definition
  const columns = [
    {
      title: "Agent & Call Info",
      key: "agentInfo",
      render: (_: any, record: CallDetail) => {
        const pKey = (record.provider || "vapi").toLowerCase();
        const providerColor = PROVIDER_COLORS[pKey] || "#1890ff";
        return (
          <Space size="middle" align="center">
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: `${providerColor}15`,
                border: `1px solid ${providerColor}30`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: providerColor,
                fontWeight: 700,
                fontSize: 14
              }}
            >
              {(record.agentName || "A")[0].toUpperCase()}
            </div>
            <div>
              <Space size={6} align="center">
                <Text strong style={{ fontSize: 14, color: token.colorTextHeading }}>
                  {record.agentName || "Voice Agent"}
                </Text>
                <Tag
                  color={providerColor}
                  style={{
                    borderRadius: 4,
                    fontWeight: 600,
                    fontSize: 10,
                    textTransform: "uppercase",
                    padding: "1px 6px",
                    lineHeight: "16px"
                  }}
                >
                  {record.provider || "Vapi"}
                </Tag>
              </Space>

              <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 2 }}>
                {record.customer && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Customer: <span style={{ color: token.colorText }}>{record.customer}</span>
                  </Text>
                )}
                <Space size={4}>
                  {record.hasRecording && (
                    <Tooltip title="Audio Recording Available">
                      <SoundOutlined style={{ fontSize: 12, color: token.colorInfo }} />
                    </Tooltip>
                  )}
                  {record.hasTranscript && (
                    <Tooltip title="Transcript Available">
                      <FileTextOutlined style={{ fontSize: 12, color: token.colorPrimary }} />
                    </Tooltip>
                  )}
                </Space>
              </div>
            </div>
          </Space>
        );
      }
    },
    {
      title: "Status & Duration",
      key: "statusDuration",
      width: 160,
      render: (_: any, record: CallDetail) => {
        const s = record.status || "Completed";
        let badgeStatus: any = "success";
        if (s.toLowerCase() === "processing") badgeStatus = "processing";
        if (s.toLowerCase() === "failed") badgeStatus = "error";
        return (
          <div>
            <Badge status={badgeStatus} text={<Text style={{ fontSize: 13, fontWeight: 500 }}>{s}</Text>} />
            <div style={{ fontSize: 11, color: token.colorTextDescription, fontFamily: "monospace", marginTop: 2 }}>
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              {record.duration || "00:00"}
            </div>
          </div>
        );
      }
    },
    {
      title: "Health Score",
      key: "healthScore",
      width: 150,
      render: (_: any, record: CallDetail) => {
        if (record.score === null || record.score === undefined) {
          return (
            <Tag color="default" style={{ fontSize: 11, borderRadius: 4 }}>
              Pending Evaluation
            </Tag>
          );
        }
        const color = getScoreColor(record.score);
        return (
          <Space size={6} align="center">
            <Text style={{ fontWeight: 700, fontSize: 15, color }}>{record.score}</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>/ 100</Text>
            {record.grade ? (
              <Tag color={color} style={{ fontWeight: 700, borderRadius: 4, fontSize: 11, padding: "0 6px" }}>
                {record.grade}
              </Tag>
            ) : null}
          </Space>
        );
      }
    },
    {
      title: "Voice Quality (NISQA)",
      key: "voiceQuality",
      width: 170,
      render: (_: any, record: CallDetail) => {
        const rawMos = record.rawMetrics?.mos_score;
        const vq = record.voiceQuality;
        if (rawMos !== undefined && rawMos !== null) {
          const color = rawMos >= 4.0 ? token.colorSuccess : rawMos >= 3.0 ? token.colorWarning : token.colorError;
          return (
            <Tooltip title={`NISQA Mean Opinion Score: ${rawMos} / 5.0`}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Tag
                  style={{
                    color,
                    background: `${color}15`,
                    borderColor: `${color}30`,
                    fontWeight: 700,
                    borderRadius: 6,
                    fontSize: 12,
                    margin: 0
                  }}
                >
                  {rawMos.toFixed(2)} MOS
                </Tag>
              </div>
            </Tooltip>
          );
        }
        if (vq !== undefined && vq !== null) {
          return (
            <Tag color={vq >= 80 ? "success" : "warning"} style={{ borderRadius: 6, fontWeight: 600, margin: 0 }}>
              {vq}% Quality
            </Tag>
          );
        }
        return <Text type="secondary" style={{ fontSize: 12 }}>—</Text>;
      }
    },
    {
      title: "Emotion",
      dataIndex: "emotion",
      key: "emotion",
      width: 140,
      render: (emotion: string | null) => {
        if (!emotion) return <Text type="secondary" style={{ fontSize: 12 }}>—</Text>;
        const emoLower = emotion.toLowerCase();
        let color = "blue";
        if (["joy", "optimism", "admiration", "approval", "caring", "excitement"].includes(emoLower)) color = "green";
        if (["anger", "annoyance", "disapproval", "disgust", "frustration"].includes(emoLower)) color = "volcano";
        if (["sadness", "disappointment", "grief", "remorse"].includes(emoLower)) color = "magenta";
        return (
          <Tag color={color} style={{ textTransform: "capitalize", borderRadius: 6, fontWeight: 500, fontSize: 11, margin: 0 }}>
            {emotion}
          </Tag>
        );
      }
    },
    {
      title: "Call Date",
      dataIndex: "date",
      key: "date",
      width: 160,
      render: (dateStr: string) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {dateStr}
        </Text>
      )
    },
    {
      title: "",
      key: "action",
      width: 60,
      align: "center" as const,
      render: (_: any, record: CallDetail) => (
        <Button
          type="text"
          shape="circle"
          icon={<RightOutlined style={{ fontSize: 12, color: token.colorTextDescription }} />}
          onClick={() => handleOpenCallDetail(record.id)}
        />
      )
    }
  ];

  return (
    <div style={{ padding: "28px", minHeight: "100vh", maxWidth: 1400, margin: "0 auto" }}>
      {/* Header & Sync */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <Title level={2} style={{ margin: 0, fontWeight: 700, letterSpacing: "-0.5px" }}>Conversations</Title>
          <Text type="secondary" style={{ fontSize: 14 }}>Real-time voice agent analytics, NISQA quality scores, and turn diagnostics</Text>
        </div>

        <Button
          type="primary"
          icon={<CloudDownloadOutlined />}
          onClick={handleSyncAllCalls}
          loading={syncing}
          style={{ borderRadius: 10, fontWeight: 600, height: 40, padding: "0 20px" }}
        >
          Sync Calls
        </Button>
      </div>

      {/* KPI Overview Summary Bar */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 20 }}>
        <Card size="small" style={{ borderRadius: 12, border: `1px solid ${token.colorBorderSecondary}` }}>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>Total Calls</Text>
          <div style={{ fontSize: 24, fontWeight: 700, marginTop: 4, color: token.colorTextHeading }}>
            {pagination.total || calls.length}
          </div>
        </Card>

        <Card size="small" style={{ borderRadius: 12, border: `1px solid ${token.colorBorderSecondary}` }}>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>Avg Health Score</Text>
          <div style={{ fontSize: 24, fontWeight: 700, marginTop: 4, color: avgHealth ? getScoreColor(avgHealth) : token.colorTextHeading }}>
            {avgHealth ? `${avgHealth} / 100` : "—"}
          </div>
        </Card>

        <Card size="small" style={{ borderRadius: 12, border: `1px solid ${token.colorBorderSecondary}` }}>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>Avg NISQA MOS</Text>
          <div style={{ fontSize: 24, fontWeight: 700, marginTop: 4, color: token.colorSuccess }}>
            {avgMos ? `${avgMos} MOS` : "—"}
          </div>
        </Card>

        <Card size="small" style={{ borderRadius: 12, border: `1px solid ${token.colorBorderSecondary}` }}>
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>Avg Latency</Text>
          <div style={{ fontSize: 24, fontWeight: 700, marginTop: 4, color: token.colorInfo }}>
            {avgLatency ? `${avgLatency} ms` : "—"}
          </div>
        </Card>
      </div>

      {/* Streamlined Filter Bar */}
      <Card
        bordered={false}
        style={{
          borderRadius: 14,
          marginBottom: 20,
          background: token.colorBgContainer,
          border: `1px solid ${token.colorBorderSecondary}`
        }}
        bodyStyle={{ padding: "14px 18px" }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
          {/* Wide Search Bar */}
          <Input
            placeholder="Search agent, customer name, transcript..."
            prefix={<SearchOutlined style={{ color: token.colorTextPlaceholder }} />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: 320, borderRadius: 8 }}
            allowClear
          />

          {/* Clean Dropdown Filters */}
          <Space wrap size="small">
            <Select value={providerFilter} onChange={setProviderFilter} style={{ width: 130, borderRadius: 8 }}>
              <Option value="all">All Providers</Option>
              <Option value="vapi">Vapi</Option>
              <Option value="retell">Retell</Option>
              <Option value="elevenlabs">ElevenLabs</Option>
            </Select>

            <Select value={agentFilter} onChange={setAgentFilter} style={{ width: 140, borderRadius: 8 }}>
              <Option value="all">All Agents</Option>
              {agentsList.map(a => (
                <Option key={a.id} value={a.id}>{a.name}</Option>
              ))}
            </Select>

            <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 130, borderRadius: 8 }}>
              <Option value="all">All Statuses</Option>
              <Option value="completed">Completed</Option>
              <Option value="processing">Processing</Option>
              <Option value="failed">Failed</Option>
            </Select>

            <Select value={gradeFilter} onChange={setGradeFilter} style={{ width: 120, borderRadius: 8 }}>
              <Option value="all">All Grades</Option>
              <Option value="A">Grade A (90+)</Option>
              <Option value="B">Grade B (80-89)</Option>
              <Option value="C">Grade C (70-79)</Option>
              <Option value="F">Grade F (&lt;70)</Option>
            </Select>

            <Select value={durationFilter} onChange={setDurationFilter} style={{ width: 130, borderRadius: 8 }}>
              <Option value="all">All Durations</Option>
              <Option value="lt30">&lt; 30s</Option>
              <Option value="30to120">30s - 2m</Option>
              <Option value="2mto5m">2 - 5m</Option>
              <Option value="gt5m">5m+</Option>
            </Select>

            {activeFilterCount > 0 && (
              <Button type="link" onClick={resetFilters} style={{ fontSize: 12, padding: "0 6px" }}>
                Clear ({activeFilterCount})
              </Button>
            )}
          </Space>
        </div>
      </Card>

      {/* Main Table */}
      <Card
        bordered={false}
        style={{
          borderRadius: 14,
          background: token.colorBgContainer,
          border: `1px solid ${token.colorBorderSecondary}`,
          overflow: "hidden"
        }}
        bodyStyle={{ padding: 0 }}
      >
        {error ? (
          <div style={{ padding: 24 }}>
            <Alert message="Error" description={error} type="error" showIcon />
          </div>
        ) : loading ? (
          <div style={{ padding: 24 }}>
            <Skeleton active paragraph={{ rows: 8 }} />
          </div>
        ) : calls.length === 0 ? (
          <div style={{ padding: "56px 24px", textAlign: "center" }}>
            <Empty
              description={
                <span>
                  <Title level={4} style={{ margin: "8px 0 4px" }}>No Conversations Found</Title>
                  <Text type="secondary">Adjust filters or synchronize call history to start analyzing evaluations.</Text>
                </span>
              }
            >
              <Space style={{ marginTop: 16 }}>
                <Button onClick={() => navigate("/integrations")} icon={<ApiOutlined />}>
                  Connect Provider
                </Button>
                <Button type="primary" onClick={handleSyncAllCalls} icon={<CloudDownloadOutlined />}>
                  Sync Calls
                </Button>
              </Space>
            </Empty>
          </div>
        ) : (
          <Table
            columns={columns as any}
            dataSource={calls}
            rowKey="id"
            onRow={(record) => ({
              onClick: () => handleOpenCallDetail(record.id),
              style: { cursor: "pointer" }
            })}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: pagination.total,
              showSizeChanger: true,
              pageSizeOptions: ["10", "25", "50", "100"],
              onChange: (page, pageSize) => {
                setPagination({ current: page, pageSize, total: pagination.total });
              }
            }}
          />
        )}
      </Card>

      {/* Call Detail Slide-Out Drawer */}
      <CallDetailDrawer
        open={drawerOpen}
        call={selectedCall}
        loading={drawerLoading}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedCall(null);
        }}
        onReevaluateSuccess={() => {
          fetchCalls();
          if (selectedCallId) handleOpenCallDetail(selectedCallId);
        }}
      />
    </div>
  );
};

