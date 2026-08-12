import React, { useState, useRef } from "react";
import {
  Drawer,
  Tabs,
  Tag,
  Typography,
  Space,
  Button,
  Row,
  Col,
  Card,
  Progress,
  Timeline,
  Badge,
  Input,
  Tooltip,
  Alert,
  Spin,
  notification,
  theme
} from "antd";
import {
  SoundOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  CodeOutlined,
  ReloadOutlined,
  CopyOutlined,
  DownloadOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  SearchOutlined,
  UserOutlined,
  RobotOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  ApiOutlined
} from "@ant-design/icons";
import { API_URL, TOKEN_KEY } from "../../providers/constants";

const { Title, Text, Paragraph } = Typography;

export interface SpeechSegment {
  speaker: string;
  start: number;
  end: number;
  text: string;
}

export interface InterruptionEvent {
  start: number;
  end: number;
  duration: number;
  interrupter: string;
  interrupted: string;
  type: string;
  barge_in_status?: string | null;
}

export interface InterruptionDetails {
  user_to_ai_interruptions: number;
  ai_to_user_interruptions: number;
  total_interruption_events: number;
  avg_overlap_duration_sec: number;
  longest_interruption_sec: number;
  interruptions_per_minute: number;
  barge_ins_accepted: number;
  barge_ins_ignored: number;
  events?: InterruptionEvent[];
}

export interface CallDetail {
  id: string;
  agentId: string;
  agentName: string;
  projectId: string;
  provider: string;
  externalId: string;
  score?: number | null;
  grade?: string | null;
  duration: string;
  durationSec: number;
  status: string;
  date: string;
  startedAt?: string | null;
  endedAt?: string | null;
  cost?: number | null;
  audioUrl?: string | null;
  latencyMs?: number | null;
  interruptions?: number | null;
  deadAirPercent?: number | null;
  speechRateWpm?: number | null;
  emotion?: string | null;
  voiceQuality?: number | null;
  customer?: string | null;
  hasRecording: boolean;
  hasTranscript: boolean;
  emotionTimeline: string[];
  detectedIssues: string[];
  segments: SpeechSegment[];
  interruptionDetails?: InterruptionDetails | null;
  rawMetrics?: any;
}

interface CallDetailDrawerProps {
  open: boolean;
  call: CallDetail | null;
  loading?: boolean;
  onClose: () => void;
  onReevaluateSuccess?: () => void;
}

const PROVIDER_COLORS: Record<string, string> = {
  vapi: "#8b5cf6",
  retell: "#10b981",
  elevenlabs: "#f59e0b",
  bolna: "#0ea5e9"
};

export const CallDetailDrawer: React.FC<CallDetailDrawerProps> = ({
  open,
  call,
  loading,
  onClose,
  onReevaluateSuccess
}) => {
  const { token } = theme.useToken();
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [reevaluating, setReevaluating] = useState<boolean>(false);
  const [transcriptSearch, setTranscriptSearch] = useState<string>("");
  const [playbackRate, setPlaybackRate] = useState<number>(1.0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  if (!call && !loading) return null;

  // Extract and calculate tool call metrics
  const toolCalls = call?.rawMetrics?.tool_calls || [];
  const validLatencies = toolCalls
    .map((tc: any) => tc.latency_ms)
    .filter((lat: any) => lat !== null && lat !== undefined);

  const totalToolCalls = toolCalls.length;
  const avgLatency = validLatencies.length > 0
    ? Math.round(validLatencies.reduce((sum: number, lat: number) => sum + lat, 0) / validLatencies.length)
    : null;

  const slowestTool = toolCalls.reduce((slowest: any, current: any) => {
    if (current.latency_ms === null || current.latency_ms === undefined) return slowest;
    if (!slowest || current.latency_ms > slowest.latency_ms) return current;
    return slowest;
  }, null);

  const isValidJson = (str: any) => {
    if (typeof str !== "string") return false;
    try {
      JSON.parse(str);
      return true;
    } catch (e) {
      return false;
    }
  };

  const formatCost = (val: number | null | undefined): string => {
    if (val === null || val === undefined) return "—";
    if (val === 0) return "$0.00";
    if (val < 0.01) {
      // Sub-penny costs: show up to 4 decimals, prune trailing zeros (e.g. $0.0045)
      return `$${parseFloat(val.toFixed(4))}`;
    }
    // Standard cents or higher: show up to 3 decimals, prune trailing zeros
    // This formats 0.0450 to $0.045 and 1.2500 to $1.25 nicely
    const formatted = parseFloat(val.toFixed(3));
    // Ensure at least 2 decimal places are shown for normal values (e.g. $0.1 -> $0.10)
    const str = formatted.toString();
    const parts = str.split(".");
    if (parts.length === 1) {
      return `$${str}.00`;
    }
    if (parts[1].length === 1) {
      return `$${str}0`;
    }
    return `$${str}`;
  };

  const handleReevaluate = async () => {
    if (!call) return;
    setReevaluating(true);
    try {
      const tokenVal = localStorage.getItem(TOKEN_KEY);
      const res = await fetch(`${API_URL}/conversations/${call.id}/reevaluate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${tokenVal}` }
      });
      if (!res.ok) throw new Error("Re-evaluation request failed");
      notification.success({
        message: "Re-evaluation Triggered",
        description: "Background processing started for this call.",
        placement: "bottomRight"
      });
      if (onReevaluateSuccess) onReevaluateSuccess();
    } catch (err: any) {
      notification.error({
        message: "Error",
        description: err.message || "Failed to trigger re-evaluation",
        placement: "bottomRight"
      });
    } finally {
      setReevaluating(false);
    }
  };

  const copyRawJson = () => {
    if (!call) return;
    navigator.clipboard.writeText(JSON.stringify(call.rawMetrics || call, null, 2));
    notification.info({
      message: "Copied to Clipboard",
      description: "Raw call payload copied successfully.",
      placement: "bottomRight"
    });
  };

  const handlePlaybackRateChange = (rate: number) => {
    setPlaybackRate(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  };

  const seekAudio = (startTime: number) => {
    setActiveTab("transcript");
    setTimeout(() => {
      if (audioRef.current) {
        audioRef.current.currentTime = startTime;
        audioRef.current.play().catch(() => {});
        setIsPlaying(true);
      }
    }, 150);
  };

  const providerKey = (call?.provider || "vapi").toLowerCase();
  const providerColor = PROVIDER_COLORS[providerKey] || "#1890ff";
  const intDetails: InterruptionDetails | undefined = call?.interruptionDetails || call?.rawMetrics?.interruption_details;

  const getScoreColor = (score: number) => {
    if (score >= 90) return token.colorSuccess;
    if (score >= 70) return token.colorWarning;
    return token.colorError;
  };

  const filteredSegments = (call?.segments || []).filter((seg) =>
    transcriptSearch ? seg.text.toLowerCase().includes(transcriptSearch.toLowerCase()) : true
  );

  return (
    <Drawer
      title={null}
      placement="right"
      width={720}
      open={open}
      onClose={onClose}
      bodyStyle={{ padding: 0, background: token.colorBgContainer }}
    >
      {loading || !call ? (
        <div style={{ padding: 48, textAlign: "center" }}>
          <Spin size="large" tip="Loading call details..." />
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
          {/* Header Banner */}
          <div
            style={{
              padding: "24px",
              background: `linear-gradient(135deg, ${providerColor}15 0%, ${token.colorBgContainer} 100%)`,
              borderBottom: `1px solid ${token.colorBorderSecondary}`
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <Space size="middle" align="center">
                <Tag
                  color={providerColor}
                  style={{
                    borderRadius: 6,
                    padding: "4px 10px",
                    fontSize: 12,
                    fontWeight: 600,
                    textTransform: "uppercase"
                  }}
                >
                  <ApiOutlined style={{ marginRight: 6 }} />
                  {call.provider}
                </Tag>
                <Tag color={call.status === "Completed" ? "success" : "processing"}>
                  {call.status}
                </Tag>
              </Space>

              <Button
                icon={<ReloadOutlined spin={reevaluating} />}
                onClick={handleReevaluate}
                loading={reevaluating}
                size="small"
                style={{ borderRadius: 6 }}
              >
                Re-evaluate Call
              </Button>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
              <div>
                <Title level={3} style={{ margin: 0, fontWeight: 600 }}>
                  {call.agentName}
                </Title>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  Call ID: {call.externalId || call.id}
                </Text>
              </div>

              <div style={{ textAlign: "right" }}>
                {call.score !== null && call.score !== undefined ? (
                  <div style={{ display: "flex", alignItems: "baseline", gap: 6, justifyContent: "flex-end" }}>
                    <Text style={{ fontSize: 28, fontWeight: 700, color: getScoreColor(call.score) }}>
                      {call.score}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 14 }}>/ 100</Text>
                    {call.grade ? (
                      <Tag
                        color={getScoreColor(call.score)}
                        style={{ marginLeft: 6, fontWeight: 700, fontSize: 14, padding: "2px 8px" }}
                      >
                        {call.grade}
                      </Tag>
                    ) : null}
                  </div>
                ) : (
                  <Tag color="default" style={{ fontSize: 12 }}>
                    Not evaluated
                  </Tag>
                )}
                <div style={{ marginTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Duration: {call.duration || "—"} • {call.date}
                  </Text>
                </div>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div style={{ padding: "0 24px", borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={[
                { key: "overview", label: <span><InfoCircleOutlined /> Overview & Metrics</span> },
                { key: "transcript", label: <span><FileTextOutlined /> Audio & Transcript ({call.segments.length})</span> },
                (call?.rawMetrics?.tool_calls && call.rawMetrics.tool_calls.length > 0) ? {
                  key: "tool_calls",
                  label: <span><ApiOutlined /> Tool Calls ({call.rawMetrics.tool_calls.length})</span>
                } : null,
                { key: "metadata", label: <span><CodeOutlined /> Technical Metadata</span> }
              ].filter(Boolean) as any}
            />
          </div>

          {/* Tab Content Container */}
          <div style={{ padding: "24px", overflowY: "auto", flexGrow: 1 }}>
            {/* OVERVIEW & METRICS TAB */}
            {activeTab === "overview" && (
              <Space direction="vertical" size="large" style={{ width: "100%" }}>
                {/* Overall Health & NISQA Summary Cards */}
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>Evaluation Breakdown</Title>
                  <Row gutter={[12, 12]}>
                    <Col span={12}>
                      <Card size="small" style={{ borderRadius: 12, padding: 12 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>Overall Health Score</Text>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginTop: 4 }}>
                          <Title level={3} style={{ margin: 0, color: call.score !== null && call.score !== undefined ? getScoreColor(call.score) : token.colorTextDescription }}>
                            {call.score !== null && call.score !== undefined ? `${call.score} / 100` : "N/A"}
                          </Title>
                          {call.grade && <Tag color={getScoreColor(call.score!)} style={{ fontWeight: 700 }}>Grade {call.grade}</Tag>}
                        </div>
                        {call.score !== null && call.score !== undefined && (
                          <Progress percent={call.score} strokeColor={getScoreColor(call.score)} size="small" style={{ marginTop: 8 }} />
                        )}
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card size="small" style={{ borderRadius: 12, padding: 12 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>NISQA Speech Quality (MOS)</Text>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginTop: 4 }}>
                          <Title level={3} style={{ margin: 0, color: token.colorSuccess }}>
                            {call.rawMetrics?.mos_score !== undefined && call.rawMetrics?.mos_score !== null
                              ? `${call.rawMetrics.mos_score.toFixed(2)} MOS`
                              : call.voiceQuality !== null && call.voiceQuality !== undefined
                              ? `${call.voiceQuality}%`
                              : "N/A"}
                          </Title>
                          <Tag color="success" style={{ fontWeight: 600 }}>Deep Learning</Tag>
                        </div>
                        {call.rawMetrics?.mos_score !== undefined && call.rawMetrics?.mos_score !== null && (
                          <Progress
                            percent={Math.round((call.rawMetrics.mos_score / 5.0) * 100)}
                            strokeColor={token.colorSuccess}
                            size="small"
                            style={{ marginTop: 8 }}
                            format={() => `${call.rawMetrics.mos_score.toFixed(2)} / 5.0`}
                          />
                        )}
                      </Card>
                    </Col>
                  </Row>
                </div>

                {/* Grid of Real Performance Metrics */}
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>Call Performance Telemetry</Title>
                  <Row gutter={[12, 12]}>
                    <Col span={8}>
                      <Card size="small" style={{ borderRadius: 10, textAlign: "center" }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>Response Latency</Text>
                        <Title level={4} style={{ margin: "4px 0 0" }}>
                          {call.latencyMs !== null && call.latencyMs !== undefined ? `${call.latencyMs} ms` : "—"}
                        </Title>
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" style={{ borderRadius: 10, textAlign: "center" }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>Dead Air Ratio</Text>
                        <Title level={4} style={{ margin: "4px 0 0" }}>
                          {call.deadAirPercent !== null && call.deadAirPercent !== undefined ? `${call.deadAirPercent.toFixed(1)}%` : "—"}
                        </Title>
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" style={{ borderRadius: 10, textAlign: "center" }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>Speech Rate</Text>
                        <Title level={4} style={{ margin: "4px 0 0" }}>
                          {call.speechRateWpm !== null && call.speechRateWpm !== undefined ? `${call.speechRateWpm} WPM` : "—"}
                        </Title>
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" style={{ borderRadius: 10, textAlign: "center" }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>Estimated Cost</Text>
                        <Title level={4} style={{ margin: "4px 0 0" }}>
                          {formatCost(call.cost)}
                        </Title>
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card
                        size="small"
                        style={{
                          borderRadius: 10,
                          textAlign: "center",
                          cursor: (intDetails?.events && intDetails.events.length > 0) ? "pointer" : "default"
                        }}
                        onClick={() => {
                          if (intDetails?.events && intDetails.events.length > 0) {
                            seekAudio(intDetails.events[0].start);
                          }
                        }}
                      >
                        <Text type="secondary" style={{ fontSize: 12 }}>Interruptions</Text>
                        <Title level={4} style={{ margin: "4px 0 0" }}>
                          {call.interruptions !== null && call.interruptions !== undefined ? call.interruptions : "—"}
                        </Title>
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" style={{ borderRadius: 10, textAlign: "center" }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>Total Turns</Text>
                        <Title level={4} style={{ margin: "4px 0 0" }}>
                          {call.segments ? call.segments.length : "—"}
                        </Title>
                      </Card>
                    </Col>
                  </Row>
                </div>

                {/* Interruption & Barge-in Telemetry */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <Title level={5} style={{ margin: 0 }}>Interruption & Barge-in Telemetry</Title>
                    <Tag color="purple" style={{ fontWeight: 600 }}>Real Signal Analysis</Tag>
                  </div>
                  <Card size="small" style={{ borderRadius: 12, padding: 12 }}>
                    <Row gutter={[12, 12]}>
                      <Col span={12}>
                        <div
                          style={{
                            padding: "8px 12px",
                            background: token.colorFillQuaternary,
                            borderRadius: 8,
                            cursor: intDetails?.events?.some(e => e.type === "user_to_ai") ? "pointer" : "default"
                          }}
                          onClick={() => {
                            const match = intDetails?.events?.find(e => e.type === "user_to_ai");
                            if (match) seekAudio(match.start);
                          }}
                        >
                          <Text type="secondary" style={{ fontSize: 11, display: "block" }}>User → AI Interruptions</Text>
                          <Text style={{ fontSize: 18, fontWeight: 700, color: token.colorWarning }}>
                            {intDetails?.user_to_ai_interruptions ?? "—"}
                          </Text>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div
                          style={{
                            padding: "8px 12px",
                            background: token.colorFillQuaternary,
                            borderRadius: 8,
                            cursor: intDetails?.events?.some(e => e.type === "ai_to_user") ? "pointer" : "default"
                          }}
                          onClick={() => {
                            const match = intDetails?.events?.find(e => e.type === "ai_to_user");
                            if (match) seekAudio(match.start);
                          }}
                        >
                          <Text type="secondary" style={{ fontSize: 11, display: "block" }}>AI → User Interruptions</Text>
                          <Text style={{ fontSize: 18, fontWeight: 700, color: token.colorWarning }}>
                            {intDetails?.ai_to_user_interruptions ?? "—"}
                          </Text>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div
                          style={{
                            padding: "8px 12px",
                            background: token.colorFillQuaternary,
                            borderRadius: 8,
                            cursor: (intDetails?.events && intDetails.events.length > 0) ? "pointer" : "default"
                          }}
                          onClick={() => {
                            if (intDetails?.events && intDetails.events.length > 0) {
                              seekAudio(intDetails.events[0].start);
                            }
                          }}
                        >
                          <Text type="secondary" style={{ fontSize: 11, display: "block" }}>Total Interruption Events</Text>
                          <Text style={{ fontSize: 18, fontWeight: 700, color: token.colorText }}>
                            {intDetails?.total_interruption_events ?? "—"}
                          </Text>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div style={{ padding: "8px 12px", background: token.colorFillQuaternary, borderRadius: 8 }}>
                          <Text type="secondary" style={{ fontSize: 11, display: "block" }}>Interruptions per Minute</Text>
                          <Text style={{ fontSize: 18, fontWeight: 700, color: token.colorText }}>
                            {intDetails?.interruptions_per_minute !== undefined ? `${intDetails.interruptions_per_minute} / min` : "—"}
                          </Text>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div style={{ padding: "8px 12px", background: token.colorFillQuaternary, borderRadius: 8 }}>
                          <Text type="secondary" style={{ fontSize: 11, display: "block" }}>Average Overlap Duration</Text>
                          <Text style={{ fontSize: 18, fontWeight: 700, color: token.colorInfo }}>
                            {intDetails?.avg_overlap_duration_sec !== undefined ? `${intDetails.avg_overlap_duration_sec}s` : "—"}
                          </Text>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div
                          style={{
                            padding: "8px 12px",
                            background: token.colorFillQuaternary,
                            borderRadius: 8,
                            cursor: (intDetails?.events && intDetails.events.length > 0) ? "pointer" : "default"
                          }}
                          onClick={() => {
                            if (intDetails?.events && intDetails.events.length > 0) {
                              const sortedByDur = [...intDetails.events].sort((a, b) => b.duration - a.duration);
                              seekAudio(sortedByDur[0].start);
                            }
                          }}
                        >
                          <Text type="secondary" style={{ fontSize: 11, display: "block" }}>Longest Interruption</Text>
                          <Text style={{ fontSize: 18, fontWeight: 700, color: token.colorError }}>
                            {intDetails?.longest_interruption_sec !== undefined ? `${intDetails.longest_interruption_sec}s` : "—"}
                          </Text>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div
                          style={{
                            padding: "8px 12px",
                            background: token.colorFillQuaternary,
                            borderRadius: 8,
                            cursor: intDetails?.events?.some(e => e.barge_in_status === "accepted") ? "pointer" : "default"
                          }}
                          onClick={() => {
                            const match = intDetails?.events?.find(e => e.barge_in_status === "accepted");
                            if (match) seekAudio(match.start);
                          }}
                        >
                          <Text type="secondary" style={{ fontSize: 11, display: "block" }}>Barge-ins Accepted (AI Backed Off)</Text>
                          <Text style={{ fontSize: 18, fontWeight: 700, color: token.colorSuccess }}>
                            {intDetails?.barge_ins_accepted ?? "—"}
                          </Text>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div
                          style={{
                            padding: "8px 12px",
                            background: token.colorFillQuaternary,
                            borderRadius: 8,
                            cursor: intDetails?.events?.some(e => e.barge_in_status === "ignored") ? "pointer" : "default"
                          }}
                          onClick={() => {
                            const match = intDetails?.events?.find(e => e.barge_in_status === "ignored");
                            if (match) seekAudio(match.start);
                          }}
                        >
                          <Text type="secondary" style={{ fontSize: 11, display: "block" }}>Barge-ins Ignored (Double-talk Clash)</Text>
                          <Text style={{ fontSize: 18, fontWeight: 700, color: token.colorError }}>
                            {intDetails?.barge_ins_ignored ?? "—"}
                          </Text>
                        </div>
                      </Col>
                    </Row>

                    {/* Interactive Timestamps Stream */}
                    {intDetails?.events && intDetails.events.length > 0 && (
                      <div style={{ marginTop: 16, paddingTop: 12, borderTop: `1px dashed ${token.colorBorderSecondary}` }}>
                        <Text type="secondary" style={{ fontSize: 11, fontWeight: 600, display: "block", marginBottom: 8 }}>
                          INTERRUPTION EVENT TIMESTAMPS (CLICK TO SEEK AUDIO):
                        </Text>
                        <Space wrap size={[6, 6]}>
                          {intDetails.events.map((ev, idx) => {
                            const isUserToAi = ev.type === "user_to_ai";
                            const isAccepted = ev.barge_in_status === "accepted";
                            const tagColor = isUserToAi ? (isAccepted ? "success" : "warning") : "processing";
                            return (
                              <Tooltip
                                key={idx}
                                title={`Click to jump to ${ev.start.toFixed(1)}s in audio (${ev.interrupter} interrupted ${ev.interrupted})`}
                              >
                                <Tag
                                  color={tagColor}
                                  onClick={() => seekAudio(ev.start)}
                                  style={{
                                    cursor: "pointer",
                                    borderRadius: 6,
                                    padding: "2px 8px",
                                    fontSize: 12,
                                    fontWeight: 600,
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: 4
                                  }}
                                >
                                  <PlayCircleOutlined style={{ fontSize: 11 }} />
                                  <span>{ev.start.toFixed(1)}s - {ev.end.toFixed(1)}s</span>
                                  <span style={{ opacity: 0.75, fontSize: 10 }}>({ev.duration}s {ev.type === "user_to_ai" ? "User→AI" : "AI→User"})</span>
                                </Tag>
                              </Tooltip>
                            );
                          })}
                        </Space>
                      </div>
                    )}
                  </Card>
                </div>

                {/* Detected Issues */}
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>Detected Friction & Alerts</Title>
                  {call.detectedIssues && call.detectedIssues.length > 0 ? (
                    <Space direction="vertical" style={{ width: "100%" }}>
                      {call.detectedIssues.map((issue, idx) => (
                        <Alert key={idx} message={issue} type="warning" showIcon style={{ borderRadius: 8 }} />
                      ))}
                    </Space>
                  ) : (
                    <Alert message="No critical friction issues or high-latency bottlenecks detected." type="info" showIcon style={{ borderRadius: 8 }} />
                  )}
                </div>

                {/* Sentiment & Emotion Timeline */}
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>Sentiment & Emotion Insight</Title>
                  <Card size="small" style={{ borderRadius: 10, padding: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                      <Text type="secondary">Primary Customer Sentiment:</Text>
                      <Tag color="blue" style={{ textTransform: "capitalize", fontWeight: 600 }}>
                        {call.emotion || "Neutral"}
                      </Tag>
                    </div>
                    {call.emotionTimeline && call.emotionTimeline.length > 0 ? (
                      <div style={{ display: "flex", justifyContent: "space-around", fontSize: 22, padding: "8px 0" }}>
                        {call.emotionTimeline.map((emoji, i) => (
                          <Tooltip key={i} title={`Segment Turn ${i + 1}`}>
                            <span>{emoji}</span>
                          </Tooltip>
                        ))}
                      </div>
                    ) : null}
                  </Card>
                </div>
              </Space>
            )}

            {/* AUDIO & TRANSCRIPT TAB */}
            {activeTab === "transcript" && (
              <Space direction="vertical" size="large" style={{ width: "100%" }}>
                {/* Integrated Audio Player */}
                {call.audioUrl ? (
                  <Card size="small" style={{ borderRadius: 12, padding: 16, background: token.colorFillQuaternary }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                      <Space size="small">
                        <SoundOutlined style={{ color: providerColor, fontSize: 18 }} />
                        <Text strong>Call Audio Recording</Text>
                      </Space>

                      <Space size={4}>
                        <Text type="secondary" style={{ fontSize: 11 }}>Speed:</Text>
                        {[1.0, 1.25, 1.5, 2.0].map((rate) => (
                          <Button
                            key={rate}
                            size="small"
                            type={playbackRate === rate ? "primary" : "default"}
                            onClick={() => handlePlaybackRateChange(rate)}
                            style={{ borderRadius: 4, fontSize: 11, padding: "0 6px" }}
                          >
                            {rate}x
                          </Button>
                        ))}
                        <Button
                          type="link"
                          size="small"
                          icon={<DownloadOutlined />}
                          href={call.audioUrl}
                          target="_blank"
                          download
                        />
                      </Space>
                    </div>

                    <audio
                      ref={audioRef}
                      src={call.audioUrl}
                      onEnded={() => setIsPlaying(false)}
                      style={{ width: "100%", height: 36 }}
                      controls
                    />
                  </Card>
                ) : null}

                {/* Searchable Transcript Stream */}
                {call.segments && call.segments.length > 0 ? (
                  <div>
                    <Input
                      placeholder="Search transcript turns..."
                      prefix={<SearchOutlined style={{ color: token.colorTextPlaceholder }} />}
                      value={transcriptSearch}
                      onChange={(e) => setTranscriptSearch(e.target.value)}
                      style={{ marginBottom: 16, borderRadius: 8 }}
                      allowClear
                    />

                    {filteredSegments.length === 0 ? (
                      <Alert message="No matching transcript turns found." type="info" showIcon />
                    ) : (
                      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                        {filteredSegments.map((seg, idx) => {
                          const isUser = seg.speaker.toLowerCase().includes("user") || seg.speaker.toLowerCase().includes("customer");
                          return (
                            <div
                              key={idx}
                              style={{
                                display: "flex",
                                flexDirection: "column",
                                alignItems: isUser ? "flex-start" : "flex-end",
                                width: "100%"
                              }}
                            >
                              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                                {isUser ? <UserOutlined style={{ fontSize: 12 }} /> : <RobotOutlined style={{ fontSize: 12, color: providerColor }} />}
                                <Text type="secondary" style={{ fontSize: 11, fontWeight: 600 }}>
                                  {isUser ? "Customer" : call.agentName}
                                </Text>
                                <Text
                                  type="secondary"
                                  style={{ fontSize: 11, cursor: call.audioUrl ? "pointer" : "default", textDecoration: call.audioUrl ? "underline" : "none" }}
                                  onClick={() => seekAudio(seg.start)}
                                >
                                  [{seg.start.toFixed(1)}s - {seg.end.toFixed(1)}s]
                                </Text>
                              </div>

                              <div
                                style={{
                                  maxWidth: "85%",
                                  padding: "10px 14px",
                                  borderRadius: isUser ? "4px 14px 14px 14px" : "14px 4px 14px 14px",
                                  background: isUser ? token.colorFillTertiary : `rgba(${parseInt(providerColor.slice(1, 3), 16)}, ${parseInt(providerColor.slice(3, 5), 16)}, ${parseInt(providerColor.slice(5, 7), 16)}, 0.12)`,
                                  border: `1px solid ${isUser ? token.colorBorderSecondary : providerColor + "33"}`
                                }}
                              >
                                <Paragraph style={{ margin: 0, fontSize: 13, lineHeight: 1.5 }}>
                                  {seg.text}
                                </Paragraph>
                              </div>
                            </div>
                          );
                        })}
                      </Space>
                    )}
                  </div>
                ) : (
                  <div style={{ padding: "32px 16px", textAlign: "center" }}>
                    <Alert
                      message="Transcript Not Imported"
                      description="No transcript turns available for this conversation."
                      type="info"
                      showIcon
                      style={{ borderRadius: 8 }}
                    />
                  </div>
                )}
              </Space>
            )}

            {/* TOOL CALLS TAB */}
            {activeTab === "tool_calls" && (
              <Space direction="vertical" size="large" style={{ width: "100%" }}>
                {/* Metrics Summary Cards */}
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>Tool Execution Metrics</Title>
                  <Row gutter={[12, 12]}>
                    <Col span={8}>
                      <Card size="small" style={{ borderRadius: 10, textAlign: "center", padding: "10px 0" }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>Total Tool Calls</Text>
                        <Title level={3} style={{ margin: "4px 0 0", color: token.colorPrimary }}>
                          {totalToolCalls}
                        </Title>
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" style={{ borderRadius: 10, textAlign: "center", padding: "10px 0" }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>Average Latency</Text>
                        <Title level={3} style={{ margin: "4px 0 0", color: avgLatency && avgLatency > 1500 ? token.colorError : (avgLatency && avgLatency > 750 ? token.colorWarning : token.colorSuccess) }}>
                          {avgLatency !== null ? `${avgLatency} ms` : "—"}
                        </Title>
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" style={{ borderRadius: 10, textAlign: "center", padding: "10px 0" }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>Slowest Execution</Text>
                        <Title level={4} style={{ margin: "6px 0 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={slowestTool ? `${slowestTool.name} (${slowestTool.latency_ms}ms)` : "—"}>
                          {slowestTool ? slowestTool.name : "—"}
                        </Title>
                        {slowestTool && (
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            {slowestTool.latency_ms} ms
                          </Text>
                        )}
                      </Card>
                    </Col>
                  </Row>
                </div>

                {/* Interactive Tool Timeline */}
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>Timeline & Latency Profile</Title>
                  {toolCalls.length > 0 ? (
                    <Timeline
                      mode="left"
                      items={toolCalls.map((tc: any) => {
                        const hasLatency = tc.latency_ms !== null && tc.latency_ms !== undefined;
                        let latencyColor = "green";
                        if (hasLatency) {
                          if (tc.latency_ms > 1500) latencyColor = "red";
                          else if (tc.latency_ms > 700) latencyColor = "orange";
                        }
                        
                        const isFailed = tc.error || (tc.result && (
                          (typeof tc.result === "string" && (tc.result.toLowerCase().includes("error") || tc.result.toLowerCase().includes("failed"))) ||
                          (typeof tc.result === "object" && (tc.result.error || tc.result.status === "error" || tc.result.status === "failed"))
                        ));

                        return {
                          dot: <ApiOutlined style={{ fontSize: "16px", color: isFailed ? token.colorError : token.colorPrimary }} />,
                          children: (
                            <Card
                              size="small"
                              style={{
                                borderRadius: 12,
                                border: isFailed ? `1px solid ${token.colorErrorBorder}` : `1px solid ${token.colorBorderSecondary}`,
                                background: isFailed ? token.colorErrorBg : token.colorBgContainer,
                                marginBottom: 12,
                                boxShadow: "0 1px 2px rgba(0,0,0,0.02)"
                              }}
                            >
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                  <Text strong style={{ fontSize: 14 }}>{tc.name}</Text>
                                  {isFailed && <Tag color="error">Failed</Tag>}
                                </div>
                                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                  {tc.start_time_sec !== null && tc.start_time_sec !== undefined && (
                                    <Tooltip title={call.audioUrl ? "Click to jump to this timestamp in audio" : "Start time in call"}>
                                      <Tag 
                                        color="blue" 
                                        style={{ 
                                          cursor: call.audioUrl ? "pointer" : "default", 
                                          fontWeight: 600,
                                          margin: 0
                                        }}
                                        onClick={() => {
                                          if (call.audioUrl) seekAudio(tc.start_time_sec);
                                        }}
                                      >
                                        <PlayCircleOutlined style={{ marginRight: 4 }} />
                                        {tc.start_time_sec.toFixed(1)}s
                                      </Tag>
                                    </Tooltip>
                                  )}
                                  {hasLatency && (
                                    <Tag color={latencyColor} style={{ fontWeight: 600, margin: 0 }}>
                                      {tc.latency_ms} ms
                                    </Tag>
                                  )}
                                </div>
                              </div>
                              
                              {/* Arguments and Result */}
                              <div style={{ marginTop: 12 }}>
                                <Row gutter={[8, 8]}>
                                  <Col span={12}>
                                    <Text type="secondary" style={{ fontSize: 11, display: "block", marginBottom: 4 }}>Arguments</Text>
                                    <pre style={{
                                      background: token.colorFillAlter,
                                      padding: "8px 10px",
                                      borderRadius: 6,
                                      fontSize: 11,
                                      maxHeight: 120,
                                      overflow: "auto",
                                      margin: 0,
                                      border: `1px solid ${token.colorBorderSecondary}`
                                    }}>
                                      {tc.arguments ? (
                                        typeof tc.arguments === "object" 
                                          ? JSON.stringify(tc.arguments, null, 2) 
                                          : (isValidJson(tc.arguments) ? JSON.stringify(JSON.parse(tc.arguments), null, 2) : tc.arguments)
                                      ) : "—"}
                                    </pre>
                                  </Col>
                                  <Col span={12}>
                                    <Text type="secondary" style={{ fontSize: 11, display: "block", marginBottom: 4 }}>Result / Error</Text>
                                    <pre style={{
                                      background: isFailed ? token.colorErrorBgActive : token.colorFillAlter,
                                      padding: "8px 10px",
                                      borderRadius: 6,
                                      fontSize: 11,
                                      maxHeight: 120,
                                      overflow: "auto",
                                      margin: 0,
                                      border: isFailed ? `1px solid ${token.colorErrorBorder}` : `1px solid ${token.colorBorderSecondary}`,
                                      color: isFailed ? token.colorError : token.colorText
                                    }}>
                                      {tc.error ? tc.error : (
                                        tc.result ? (
                                          typeof tc.result === "object" 
                                            ? JSON.stringify(tc.result, null, 2) 
                                            : (isValidJson(tc.result) ? JSON.stringify(JSON.parse(tc.result), null, 2) : tc.result)
                                        ) : "—"
                                      )}
                                    </pre>
                                  </Col>
                                </Row>
                              </div>
                            </Card>
                          )
                        };
                      })}
                    />
                  ) : (
                    <Alert
                      message="No Tool Calls"
                      description="No tool invocations recorded for this conversation execution."
                      type="info"
                      showIcon
                      style={{ borderRadius: 8 }}
                    />
                  )}
                </div>
              </Space>
            )}

            {/* TECHNICAL METADATA TAB */}
            {activeTab === "metadata" && (
              <Space direction="vertical" size="large" style={{ width: "100%" }}>
                <Card size="small" style={{ borderRadius: 10 }}>
                  <Space direction="vertical" size="small" style={{ width: "100%" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <Text type="secondary">Voice Provider:</Text>
                      <Text strong style={{ textTransform: "capitalize" }}>{call.provider}</Text>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <Text type="secondary">Internal Call ID:</Text>
                      <Text copyable={{ text: call.id }}>{call.id}</Text>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <Text type="secondary">External Call ID:</Text>
                      <Text copyable={{ text: call.externalId }}>{call.externalId || "—"}</Text>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <Text type="secondary">Agent Name:</Text>
                      <Text strong>{call.agentName}</Text>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <Text type="secondary">Customer Identifier:</Text>
                      <Text>{call.customer || "Not provided"}</Text>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <Text type="secondary">Cost:</Text>
                      <Text>{formatCost(call.cost)}</Text>
                    </div>
                  </Space>
                </Card>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <Title level={5} style={{ margin: 0 }}>Raw Evaluation Payload</Title>
                    <Button icon={<CopyOutlined />} onClick={copyRawJson} size="small">
                      Copy JSON
                    </Button>
                  </div>
                  <pre
                    style={{
                      background: token.colorFillQuaternary,
                      padding: 16,
                      borderRadius: 8,
                      fontSize: 12,
                      maxHeight: 400,
                      overflow: "auto"
                    }}
                  >
                    {JSON.stringify(call.rawMetrics || call, null, 2)}
                  </pre>
                </div>
              </Space>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
};
