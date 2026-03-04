import React, { useState, useEffect, useRef } from "react";
import { Row, Col, Card, Statistic, Tag, Button, Typography, Space, Progress, Collapse, Timeline, Tooltip, List } from "antd";
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  WarningOutlined,
  CodeOutlined,
  CustomerServiceOutlined
} from "@ant-design/icons";
import { useParams, useNavigate } from "react-router";
import { mockConversations } from "../../providers/mockData";

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

export const ConversationShow: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Find conversation
  const conv = mockConversations.find((c) => c.id === id) || mockConversations[0];

  // Player State
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const playIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const duration = conv.durationSec;

  useEffect(() => {
    if (isPlaying) {
      playIntervalRef.current = setInterval(() => {
        setCurrentTime((prev) => {
          if (prev >= duration) {
            setIsPlaying(false);
            if (playIntervalRef.current) clearInterval(playIntervalRef.current);
            return 0;
          }
          return prev + 1;
        });
      }, 1000);
    } else {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    }

    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
  }, [isPlaying, duration]);

  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const handleSliderClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const width = rect.width;
    const clickedTime = Math.floor((clickX / width) * duration);
    setCurrentTime(clickedTime);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  return (
    <div style={{ padding: "4px" }}>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate("/conversations")}
        style={{ marginBottom: "20px" }}
      >
        Back to Conversations
      </Button>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <Title level={2} style={{ margin: 0 }}>Conversation #{conv.id}</Title>
              <Text type="secondary">Recorded on: {conv.date} | Agent: </Text>
              <Tag color="blue">{conv.agentName}</Tag>
            </div>
            <div>
              <Text strong style={{ marginRight: "10px" }}>Evaluation Score</Text>
              <Progress
                type="dashboard"
                percent={conv.score}
                width={65}
                strokeColor={conv.score >= 85 ? "#52c41a" : conv.score >= 70 ? "#faad14" : "#ff4d4f"}
              />
            </div>
          </div>
        </Col>

        {/* AUDIO PLAYER & VISUAL TIMELINE */}
        <Col span={24}>
          <Card title="Interactive Playback & Turn Timeline" bordered={false}>
            {/* Audio Mock Player Control */}
            <div style={{ background: "rgba(0,0,0,0.02)", padding: "16px", borderRadius: "8px", marginBottom: "24px" }}>
              <Row gutter={16} align="middle">
                <Col>
                  <Button
                    type="primary"
                    shape="circle"
                    size="large"
                    icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                    onClick={togglePlay}
                  />
                </Col>
                <Col flex="auto">
                  <div
                    onClick={handleSliderClick}
                    style={{
                      height: "10px",
                      background: "rgba(0,0,0,0.1)",
                      borderRadius: "5px",
                      position: "relative",
                      cursor: "pointer",
                    }}
                  >
                    {/* Played Progress */}
                    <div
                      style={{
                        height: "100%",
                        width: `${(currentTime / duration) * 100}%`,
                        background: "#1890ff",
                        borderRadius: "5px",
                      }}
                    />
                    {/* Scrub Handle */}
                    <div
                      style={{
                        position: "absolute",
                        top: "-4px",
                        left: `calc(${(currentTime / duration) * 100}% - 9px)`,
                        width: "18px",
                        height: "18px",
                        borderRadius: "50%",
                        background: "#ffffff",
                        border: "3px solid #1890ff",
                        boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
                      }}
                    />
                  </div>
                </Col>
                <Col>
                  <Text strong>{formatTime(currentTime)}</Text>
                  <Text type="secondary"> / {formatTime(duration)}</Text>
                </Col>
              </Row>
            </div>

            {/* Conversation Speech Timeline */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <Text strong>Speech Turn Activity Map</Text>
                <Space>
                  <Tag color="blue">Agent Speech</Tag>
                  <Tag color="green">User Speech</Tag>
                </Space>
              </div>

              {/* Segment Bars */}
              <div
                style={{
                  height: "50px",
                  background: "rgba(0,0,0,0.04)",
                  borderRadius: "6px",
                  position: "relative",
                  overflow: "hidden",
                  border: "1px solid rgba(0,0,0,0.06)",
                }}
              >
                {conv.segments.map((seg, idx) => {
                  const left = (seg.start / duration) * 100;
                  const width = ((seg.end - seg.start) / duration) * 100;
                  const isAgent = seg.speaker === "agent";
                  const isActive = currentTime >= seg.start && currentTime <= seg.end;

                  return (
                    <Tooltip title={`${seg.speaker.toUpperCase()}: "${seg.text}"`} key={idx}>
                      <div
                        style={{
                          position: "absolute",
                          left: `${left}%`,
                          width: `${width}%`,
                          top: isAgent ? "5px" : "25px",
                          height: "20px",
                          background: isAgent ? (isActive ? "#096dd9" : "#91d5ff") : (isActive ? "#389e0d" : "#b7eb8f"),
                          borderRadius: "4px",
                          transition: "background 0.2s",
                          cursor: "pointer",
                        }}
                      />
                    </Tooltip>
                  );
                })}

                {/* Current Playhead Line */}
                <div
                  style={{
                    position: "absolute",
                    left: `${(currentTime / duration) * 100}%`,
                    top: 0,
                    bottom: 0,
                    width: "2px",
                    background: "#ff4d4f",
                    zIndex: 10,
                  }}
                />
              </div>

              {/* Current Transcript highlight */}
              <div style={{ background: "rgba(24, 144, 255, 0.03)", padding: "12px", borderRadius: "6px", borderLeft: "4px solid #1890ff" }}>
                <Text type="secondary" style={{ fontSize: "12px", display: "block" }}>Active Transcript Turn</Text>
                {(() => {
                  const activeSegment = conv.segments.find(s => currentTime >= s.start && currentTime <= s.end);
                  if (activeSegment) {
                    return (
                      <Paragraph style={{ margin: "4px 0 0 0", fontSize: "14px" }}>
                        <Text strong style={{ color: activeSegment.speaker === "agent" ? "#1890ff" : "#52c41a" }}>
                          {activeSegment.speaker === "agent" ? "Agent: " : "User: "}
                        </Text>
                        "{activeSegment.text}"
                      </Paragraph>
                    );
                  }
                  return <Text italic type="secondary" style={{ fontSize: "14px" }}>Silence / Dead Air</Text>;
                })()}
              </div>
            </div>
          </Card>
        </Col>

        {/* METRICS CARD */}
        <Col xs={24} md={16}>
          <Card title="Speech & Quality Metrics" bordered={false}>
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={8}>
                <Statistic title="Avg Latency" value={conv.latencyMs} suffix=" ms" valueStyle={{ color: conv.latencyMs > 1000 ? "#ff4d4f" : "#1890ff" }} />
              </Col>
              <Col xs={12} sm={8}>
                <Statistic title="Interruptions" value={conv.interruptions} suffix=" times" valueStyle={{ color: conv.interruptions > 3 ? "#faad14" : "#52c41a" }} />
              </Col>
              <Col xs={12} sm={8}>
                <Statistic title="Dead Air" value={conv.deadAirPercent} suffix=" %" valueStyle={{ color: conv.deadAirPercent > 10 ? "#faad14" : "#52c41a" }} />
              </Col>
              <Col xs={12} sm={8}>
                <Statistic title="Speech Rate" value={conv.speechRateWpm} suffix=" WPM" />
              </Col>
              <Col xs={12} sm={8}>
                <Statistic title="Customer Emotion" value={conv.emotion} valueStyle={{ color: conv.emotion === "Frustrated" ? "#ff4d4f" : "#52c41a" }} />
              </Col>
              <Col xs={12} sm={8}>
                <Statistic title="Voice Quality" value={conv.voiceQuality} suffix=" / 100" />
              </Col>
            </Row>

            {/* Emotion Timeline Grid */}
            <div style={{ marginTop: "24px", borderTop: "1px solid rgba(0,0,0,0.06)", paddingTop: "16px" }}>
              <Text strong style={{ display: "block", marginBottom: "8px" }}>Emotion Profile Timeline</Text>
              <div style={{ display: "flex", gap: "10px", background: "rgba(0,0,0,0.02)", padding: "10px", borderRadius: "6px" }}>
                {conv.emotionTimeline.map((emoji, idx) => (
                  <Card key={idx} size="small" style={{ textAlign: "center", width: "45px" }} bodyStyle={{ padding: "8px 0" }}>
                    <div style={{ fontSize: "20px" }}>{emoji}</div>
                    <Text type="secondary" style={{ fontSize: "10px" }}>T{idx + 1}</Text>
                  </Card>
                ))}
              </div>
            </div>
          </Card>
        </Col>

        {/* DETECTED ISSUES */}
        <Col xs={24} md={8}>
          <Card
            title={
              <Space>
                <WarningOutlined style={{ color: "#ff4d4f" }} />
                <span>Detected Health Issues</span>
              </Space>
            }
            bordered={false}
            style={{ height: "100%" }}
          >
            <List
              dataSource={conv.detectedIssues}
              renderItem={(item: string) => (
                <List.Item style={{ border: "none", padding: "8px 0" }}>
                  <Space align="start">
                    <Tag color="error">ISSUE</Tag>
                    <Text style={{ fontSize: "13px" }}>{item}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* RAW METRICS JSON */}
        <Col span={24}>
          <Collapse ghost style={{ background: "#ffffff", border: "1px solid rgba(0,0,0,0.06)", borderRadius: "8px" }}>
            <Panel
              header={
                <Space>
                  <CodeOutlined />
                  <Text strong>Evaluation Metadata (Raw JSON Payload)</Text>
                </Space>
              }
              key="json"
            >
              <pre style={{ margin: 0, padding: "12px", background: "rgba(0,0,0,0.02)", borderRadius: "6px", overflowX: "auto" }}>
                {JSON.stringify(conv.rawMetrics, null, 2)}
              </pre>
            </Panel>
          </Collapse>
        </Col>
      </Row>
    </div>
  );
};
