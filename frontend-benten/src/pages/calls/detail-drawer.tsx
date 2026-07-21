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
  elevenlabs: "#f59e0b"
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
    if (audioRef.current) {
      audioRef.current.currentTime = startTime;
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const providerKey = (call?.provider || "vapi").toLowerCase();
  const providerColor = PROVIDER_COLORS[providerKey] || "#1890ff";

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
                { key: "metadata", label: <span><CodeOutlined /> Technical Metadata</span> }
              ]}
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
                          {call.cost !== null && call.cost !== undefined ? `$${call.cost.toFixed(4)}` : "—"}
                        </Title>
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" style={{ borderRadius: 10, textAlign: "center" }}>
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
                      <Text>{call.cost !== null && call.cost !== undefined ? `$${call.cost.toFixed(4)}` : "Not provided"}</Text>
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
