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
                { key: "overview", label: <span><InfoCircleOutlined /> Overview</span> },
                { key: "transcript", label: <span><FileTextOutlined /> Transcript ({call.segments.length})</span> },
                { key: "recording", label: <span><SoundOutlined /> Recording</span> },
                { key: "evaluations", label: <span><CheckCircleOutlined /> Evaluations</span> },
                { key: "metadata", label: <span><ApiOutlined /> Metadata</span> },
                { key: "raw", label: <span><CodeOutlined /> Raw JSON</span> }
              ]}
            />
          </div>

          {/* Tab Content Container */}
          <div style={{ padding: "24px", overflowY: "auto", flexGrow: 1 }}>
            {/* OVERVIEW TAB */}
            {activeTab === "overview" && (
              <Space direction="vertical" size="large" style={{ width: "100%" }}>
                {/* Real Metric Summary Cards */}
                <Row gutter={[16, 16]}>
                  <Col span={8}>
                    <Card size="small" style={{ borderRadius: 10, textAlign: "center" }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>Latency</Text>
                      <Title level={4} style={{ margin: "4px 0 0" }}>
                        {call.latencyMs !== null && call.latencyMs !== undefined ? `${call.latencyMs} ms` : "—"}
                      </Title>
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" style={{ borderRadius: 10, textAlign: "center" }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>Dead Air</Text>
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
                      <Text type="secondary" style={{ fontSize: 12 }}>Cost</Text>
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
                      <Text type="secondary" style={{ fontSize: 12 }}>Voice Quality</Text>
                      <Title level={4} style={{ margin: "4px 0 0" }}>
                        {call.voiceQuality !== null && call.voiceQuality !== undefined ? `${call.voiceQuality}%` : "—"}
                      </Title>
                    </Card>
                  </Col>
                </Row>

                {/* Detected Issues */}
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>Detected Call Issues</Title>
                  {call.detectedIssues && call.detectedIssues.length > 0 ? (
                    <Space direction="vertical" style={{ width: "100%" }}>
                      {call.detectedIssues.map((issue, idx) => (
                        <Alert key={idx} message={issue} type="warning" showIcon style={{ borderRadius: 8 }} />
                      ))}
                    </Space>
                  ) : (
                    <Alert message="No critical friction issues detected." type="info" showIcon style={{ borderRadius: 8 }} />
                  )}
                </div>

                {/* Sentiment & Timeline */}
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>Sentiment & Emotion Timeline</Title>
                  {call.emotion || (call.emotionTimeline && call.emotionTimeline.length > 0) ? (
                    <Card size="small" style={{ borderRadius: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                        <Text type="secondary">Primary Customer Emotion:</Text>
                        <Tag color="blue" style={{ textTransform: "capitalize", fontWeight: 600 }}>
                          {call.emotion || "Unavailable"}
                        </Tag>
                      </div>
                      {call.emotionTimeline && call.emotionTimeline.length > 0 ? (
                        <div style={{ display: "flex", justifyContent: "space-around", fontSize: 22, padding: "8px 0" }}>
                          {call.emotionTimeline.map((emoji, i) => (
                            <Tooltip key={i} title={`Segment ${i + 1}`}>
                              <span>{emoji}</span>
                            </Tooltip>
                          ))}
                        </div>
                      ) : null}
                    </Card>
                  ) : (
                    <Card size="small" style={{ borderRadius: 10, textAlign: "center", padding: 16 }}>
                      <Text type="secondary">Sentiment analysis not evaluated yet.</Text>
                    </Card>
                  )}
                </div>
              </Space>
            )}

            {/* TRANSCRIPT TAB */}
            {activeTab === "transcript" && (
              <div>
                {call.segments && call.segments.length > 0 ? (
                  <div>
                    <Input
                      placeholder="Search transcript text..."
                      prefix={<SearchOutlined />}
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
                                  style={{ fontSize: 11, cursor: call.audioUrl ? "pointer" : "default" }}
                                  onClick={() => seekAudio(seg.start)}
                                >
                                  [{seg.start.toFixed(1)}s - {seg.end.toFixed(1)}s]
                                </Text>
                              </div>

                              <div
                                style={{
                                  maxWidth: "85%",
                                  padding: "12px 16px",
                                  borderRadius: isUser ? "4px 16px 16px 16px" : "16px 4px 16px 16px",
                                  background: isUser ? token.colorFillTertiary : `rgba(${parseInt(providerColor.slice(1, 3), 16)}, ${parseInt(providerColor.slice(3, 5), 16)}, ${parseInt(providerColor.slice(5, 7), 16)}, 0.12)`,
                                  border: `1px solid ${isUser ? token.colorBorderSecondary : providerColor + "33"}`
                                }}
                              >
                                <Paragraph style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}>
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
                      description="No transcript turns available for this call."
                      type="info"
                      showIcon
                      style={{ borderRadius: 8 }}
                    />
                  </div>
                )}
              </div>
            )}

            {/* RECORDING TAB */}
            {activeTab === "recording" && (
              <div>
                {call.audioUrl ? (
                  <Card style={{ borderRadius: 12, textAlign: "center", padding: 24 }}>
                    <SoundOutlined style={{ fontSize: 48, color: providerColor, marginBottom: 16 }} />
                    <Title level={4} style={{ margin: "0 0 16px" }}>Audio Recording</Title>

                    <audio
                      ref={audioRef}
                      src={call.audioUrl}
                      onEnded={() => setIsPlaying(false)}
                      style={{ width: "100%", marginBottom: 16 }}
                      controls
                    />

                    <div style={{ display: "flex", justifyContent: "center", gap: 12, alignItems: "center" }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>Playback Speed:</Text>
                      {[1.0, 1.25, 1.5, 2.0].map((rate) => (
                        <Button
                          key={rate}
                          size="small"
                          type={playbackRate === rate ? "primary" : "default"}
                          onClick={() => handlePlaybackRateChange(rate)}
                          style={{ borderRadius: 4 }}
                        >
                          {rate}x
                        </Button>
                      ))}
                      <Button
                        type="link"
                        icon={<DownloadOutlined />}
                        href={call.audioUrl}
                        target="_blank"
                        download
                      >
                        Download Audio
                      </Button>
                    </div>
                  </Card>
                ) : (
                  <div style={{ padding: "32px 16px", textAlign: "center" }}>
                    <Alert
                      message="Recording Not Available"
                      description="Audio recording is not available for this call."
                      type="warning"
                      showIcon
                      style={{ borderRadius: 8 }}
                    />
                  </div>
                )}
              </div>
            )}

            {/* EVALUATIONS TAB */}
            {activeTab === "evaluations" && (
              <div>
                {call.score !== null && call.score !== undefined ? (
                  <Space direction="vertical" size="large" style={{ width: "100%" }}>
                    <div>
                      <Title level={5} style={{ marginBottom: 16 }}>Evaluation Score Breakdown</Title>
                      <Card size="small" style={{ borderRadius: 10, padding: 16 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                          <Text strong>Overall Health Score</Text>
                          <Text style={{ fontSize: 20, fontWeight: 700, color: getScoreColor(call.score) }}>
                            {call.score} / 100
                          </Text>
                        </div>
                        <Progress percent={call.score} strokeColor={getScoreColor(call.score)} />
                      </Card>
                    </div>
                  </Space>
                ) : (
                  <div style={{ padding: "48px 16px", textAlign: "center" }}>
                    <Card style={{ borderRadius: 12 }}>
                      <CheckCircleOutlined style={{ fontSize: 40, color: token.colorTextDescription, marginBottom: 16 }} />
                      <Title level={4} style={{ margin: "0 0 8px" }}>Not Evaluated Yet</Title>
                      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
                        This call has not been evaluated by the analysis pipeline yet. Run evaluation to compute health score and quality metrics.
                      </Paragraph>
                      <Button type="primary" icon={<ReloadOutlined spin={reevaluating} />} onClick={handleReevaluate} loading={reevaluating}>
                        Run Evaluation
                      </Button>
                    </Card>
                  </div>
                )}
              </div>
            )}

            {/* METADATA TAB */}
            {activeTab === "metadata" && (
              <Card size="small" style={{ borderRadius: 10 }}>
                <Space direction="vertical" size="small" style={{ width: "100%" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <Text type="secondary">Provider:</Text>
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
            )}

            {/* RAW JSON TAB */}
            {activeTab === "raw" && (
              <div>
                <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
                  <Button icon={<CopyOutlined />} onClick={copyRawJson} size="small">
                    Copy Raw Payload
                  </Button>
                </div>
                <pre
                  style={{
                    background: token.colorFillQuaternary,
                    padding: 16,
                    borderRadius: 8,
                    fontSize: 12,
                    maxHeight: 450,
                    overflow: "auto"
                  }}
                >
                  {JSON.stringify(call.rawMetrics || call, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
};
