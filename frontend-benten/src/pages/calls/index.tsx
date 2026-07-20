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

  const columns = [
    {
      title: "Provider",
      dataIndex: "provider",
      key: "provider",
      width: 130,
      render: (provider: string) => {
        const pKey = (provider || "vapi").toLowerCase();
        const color = PROVIDER_COLORS[pKey] || "#1890ff";
        return (
          <Tag
            color={color}
            style={{
              borderRadius: 6,
              fontWeight: 600,
              fontSize: 11,
              textTransform: "uppercase",
              padding: "2px 8px"
            }}
          >
            {provider || "Vapi"}
          </Tag>
        );
      }
    },
    {
      title: "Agent",
      dataIndex: "agentName",
      key: "agentName",
      render: (name: string, record: CallDetail) => (
        <div>
          <Text strong style={{ fontSize: 14 }}>{name || "Voice Agent"}</Text>
          {record.customer ? (
            <div style={{ fontSize: 11, color: token.colorTextDescription }}>
              Customer: {record.customer}
            </div>
          ) : null}
        </div>
      )
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (status: string) => {
        const s = status || "Completed";
        let color = "success";
        if (s.toLowerCase() === "processing") color = "processing";
        if (s.toLowerCase() === "failed") color = "error";
        if (s.toLowerCase() === "cancelled") color = "default";
        return <Badge status={color as any} text={<Text style={{ fontSize: 13 }}>{s}</Text>} />;
      }
    },
    {
      title: "Duration",
      dataIndex: "duration",
      key: "duration",
      width: 110,
      render: (dur: string) => <Text style={{ fontSize: 13, fontFamily: "monospace" }}>{dur || "—"}</Text>
    },
    {
      title: "Overall Score",
      dataIndex: "score",
      key: "score",
      width: 150,
      render: (score: number | null, record: CallDetail) => {
        if (score === null || score === undefined) {
          return (
            <Tag color="default" style={{ fontSize: 11 }}>
              Not evaluated
            </Tag>
          );
        }
        const color = getScoreColor(score);
        return (
          <Space size={6} align="center">
            <Text style={{ fontWeight: 700, fontSize: 14, color }}>{score} / 100</Text>
            {record.grade ? (
              <Tag color={color} style={{ fontWeight: 700, borderRadius: 4, fontSize: 11 }}>
                {record.grade}
              </Tag>
            ) : null}
          </Space>
        );
      }
    },
    {
      title: "Call Time",
      dataIndex: "date",
      key: "date",
      width: 150,
      render: (dateStr: string) => (
        <Tooltip title={dateStr}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {dateStr}
          </Text>
        </Tooltip>
      )
    },
    {
      title: "Recording",
      dataIndex: "hasRecording",
      key: "hasRecording",
      width: 120,
      render: (hasRec: boolean) =>
        hasRec ? (
          <Tag color="cyan" icon={<SoundOutlined />}>Available</Tag>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>—</Text>
        )
    },
    {
      title: "Transcript",
      dataIndex: "hasTranscript",
      key: "hasTranscript",
      width: 120,
      render: (hasTrans: boolean) =>
        hasTrans ? (
          <Tag color="blue" icon={<FileTextOutlined />}>✓ Transcript</Tag>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>—</Text>
        )
    },
    {
      title: "Action",
      key: "action",
      width: 80,
      align: "center" as const,
      render: (_: any, record: CallDetail) => (
        <Button
          type="text"
          icon={<RightOutlined />}
          onClick={() => handleOpenCallDetail(record.id)}
        />
      )
    }
  ];

  return (
    <div style={{ padding: "24px", minHeight: "100vh" }}>
      {/* Header & Main Toolbar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <Title level={2} style={{ margin: 0, fontWeight: 600 }}>Calls</Title>
          <Text type="secondary">Browse, filter, inspect, and evaluate voice AI agent conversations</Text>
        </div>

        <Button
          type="primary"
          icon={<CloudDownloadOutlined />}
          onClick={handleSyncAllCalls}
          loading={syncing}
          style={{ borderRadius: 8, fontWeight: 500 }}
        >
          Sync Calls
        </Button>
      </div>

      {/* Filter Bar */}
      <Card
        bordered={false}
        style={{
          borderRadius: 14,
          marginBottom: 20,
          background: token.colorBgContainer,
          border: `1px solid ${token.colorBorderSecondary}`
        }}
        bodyStyle={{ padding: "16px 20px" }}
      >
        <Space wrap size="middle" style={{ width: "100%", justifyContent: "space-between" }}>
          {/* Search Box */}
          <Input
            placeholder="Search agent, call ID, transcript..."
            prefix={<SearchOutlined style={{ color: token.colorTextPlaceholder }} />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: 280, borderRadius: 8 }}
            allowClear
          />

          <Space wrap size="small">
            {/* Provider Filter */}
            <Select value={providerFilter} onChange={setProviderFilter} style={{ width: 130, borderRadius: 8 }}>
              <Option value="all">All Providers</Option>
              <Option value="vapi">Vapi</Option>
              <Option value="retell">Retell</Option>
              <Option value="elevenlabs">ElevenLabs</Option>
            </Select>

            {/* Agent Filter */}
            <Select value={agentFilter} onChange={setAgentFilter} style={{ width: 150, borderRadius: 8 }}>
              <Option value="all">All Agents</Option>
              {agentsList.map(a => (
                <Option key={a.id} value={a.id}>{a.name}</Option>
              ))}
            </Select>

            {/* Status Filter */}
            <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 130, borderRadius: 8 }}>
              <Option value="all">All Statuses</Option>
              <Option value="completed">Completed</Option>
              <Option value="processing">Processing</Option>
              <Option value="failed">Failed</Option>
            </Select>

            {/* Grade Filter */}
            <Select value={gradeFilter} onChange={setGradeFilter} style={{ width: 130, borderRadius: 8 }}>
              <Option value="all">All Grades</Option>
              <Option value="A">90+ (Grade A/A+)</Option>
              <Option value="B">80-89 (Grade B)</Option>
              <Option value="C">70-79 (Grade C)</Option>
              <Option value="F">Below 70 (Grade F)</Option>
            </Select>

            {/* Duration Filter */}
            <Select value={durationFilter} onChange={setDurationFilter} style={{ width: 130, borderRadius: 8 }}>
              <Option value="all">All Durations</Option>
              <Option value="lt30">&lt; 30 sec</Option>
              <Option value="30to120">30s - 2 min</Option>
              <Option value="2mto5m">2 - 5 min</Option>
              <Option value="gt5m">5+ min</Option>
            </Select>
          </Space>
        </Space>
      </Card>

      {/* Main Calls Table */}
      <Card
        bordered={false}
        style={{
          borderRadius: 14,
          background: token.colorBgContainer,
          border: `1px solid ${token.colorBorderSecondary}`
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
          <div style={{ padding: "48px 24px", textAlign: "center" }}>
            <Empty
              description={
                <span>
                  <Title level={4} style={{ margin: "8px 0 4px" }}>No Calls Found</Title>
                  <Text type="secondary">Connect a provider and synchronize calls to start inspecting evaluations.</Text>
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
