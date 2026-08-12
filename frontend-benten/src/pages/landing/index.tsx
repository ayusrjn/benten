import React, { useContext, useState } from "react";
import { Button, Card, Col, Drawer, Row, Space, Tooltip, Typography, theme, Divider, Timeline } from "antd";
import {
  SunOutlined,
  MoonOutlined,
  BookOutlined,
  LoginOutlined,
  UserAddOutlined,
  ArrowRightOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  PhoneOutlined,
  DashboardOutlined,
  CheckCircleOutlined,
  LineChartOutlined,
  PartitionOutlined,
  GlobalOutlined,
  SafetyOutlined,
  PlayCircleOutlined,
  GithubOutlined
} from "@ant-design/icons";
import { useNavigate } from "react-router";
import { ColorModeContext } from "../../contexts/color-mode";
import { Logo } from "../../components";
import { TOKEN_KEY } from "../../providers/constants";

const { Title, Text, Paragraph } = Typography;

export const LandingPage: React.FC = () => {
  const { mode, setMode } = useContext(ColorModeContext);
  const navigate = useNavigate();
  const [docsOpen, setDocsOpen] = useState(false);
  const isDark = mode === "dark";
  const isLoggedIn = !!localStorage.getItem(TOKEN_KEY);

  const features = [
    {
      icon: <ThunderboltOutlined style={{ fontSize: "22px", color: "#8b5cf6" }} />,
      title: "Response Latency Tracker",
      description: "Measures speech-to-response delays in milliseconds, flagging slow model inferences or network latency instantly."
    },
    {
      icon: <SafetyOutlined style={{ fontSize: "22px", color: "#3b82f6" }} />,
      title: "Acoustic NISQA Scoring",
      description: "Deep learning models score speech stream acoustics on noise, color, distortion, and return a clean MOS (1-5)."
    },
    {
      icon: <PhoneOutlined style={{ fontSize: "22px", color: "#ec4899" }} />,
      title: "Dead Air Analysis",
      description: "Detects silence rates and empty pauses, diagnosing system blockages, agent hang-ups, or prompt delays."
    },
    {
      icon: <PartitionOutlined style={{ fontSize: "22px", color: "#10b981" }} />,
      title: "Conversational Friction",
      description: "Identifies crosstalk, high overlap rates, and interruption frequencies, evaluating the quality of speaker turn-taking."
    }
  ];

  const providers = [
    { name: "Vapi AI", desc: "Sync voice assistants using instant webhooks.", color: "#8b5cf6" },
    { name: "Retell AI", desc: "Ingest conversations via API key integration.", color: "#10b981" },
    { name: "ElevenLabs", desc: "Automate conversational voice model tracking.", color: "#faad14" },
    { name: "Bolna AI", desc: "Capture real-time user-agent conversations.", color: "#0ea5e9" }
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        background: isDark ? "#090a0f" : "#fafafa",
        color: isDark ? "#f3f4f6" : "#1e293b",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        transition: "background 0.3s ease, color 0.3s ease",
        overflowX: "hidden"
      }}
    >
      <style>{`
        /* Custom Fine scrollbar & modern styles */
        body {
          margin: 0;
          font-family: inherit;
        }

        .gradient-headline {
          background: ${
            isDark
              ? "linear-gradient(to right, #ffffff 40%, #93c5fd 100%)"
              : "linear-gradient(to right, #0f172a 40%, #2563eb 100%)"
          };
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .section-container {
          max-width: 1100px;
          margin: 0 auto;
          padding: 80px 24px;
        }

        .minimal-btn {
          border-radius: 6px !important;
          font-weight: 500 !important;
          transition: all 0.2s ease !important;
        }

        .minimal-btn-primary {
          background: ${isDark ? "#ffffff" : "#0f172a"} !important;
          border-color: ${isDark ? "#ffffff" : "#0f172a"} !important;
          color: ${isDark ? "#090a0f" : "#ffffff"} !important;
        }

        .minimal-btn-primary:hover {
          opacity: 0.9;
          transform: translateY(-1px);
        }

        .minimal-btn-text {
          color: ${isDark ? "#94a3b8" : "#475569"} !important;
        }

        .minimal-btn-text:hover {
          color: ${isDark ? "#ffffff" : "#000000"} !important;
          background: ${isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(0, 0, 0, 0.02)"} !important;
        }

        .minimal-card {
          background: ${isDark ? "#11131e" : "#ffffff"} !important;
          border: 1px solid ${isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(0, 0, 0, 0.06)"} !important;
          border-radius: 12px !important;
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .minimal-card:hover {
          border-color: #3b82f6 !important;
          transform: translateY(-2px);
          box-shadow: ${isDark ? "0 10px 30px rgba(0, 0, 0, 0.4)" : "0 10px 30px rgba(0, 0, 0, 0.03)"} !important;
        }

        .border-bottom-thin {
          border-bottom: 1px solid ${isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.05)"};
        }

        .grid-visual {
          width: 100%;
          height: 380px;
          border: 1px dashed ${isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.15)"};
          border-radius: 16px;
          position: relative;
          background: ${isDark ? "rgba(255, 255, 255, 0.01)" : "rgba(0, 0, 0, 0.01)"};
          overflow: hidden;
          margin-top: 48px;
        }

        .grid-line {
          position: absolute;
          background: ${isDark ? "rgba(255, 255, 255, 0.02)" : "rgba(0, 0, 0, 0.03)"};
        }
      `}</style>

      {/* Global Glowing Lights */}
      {isDark && (
        <>
          <div style={{ position: "absolute", width: "400px", height: "400px", background: "radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, rgba(0,0,0,0) 70%)", top: "5%", left: "10%", borderRadius: "50%", filter: "blur(60px)", pointerEvents: "none" }} />
          <div style={{ position: "absolute", width: "500px", height: "500px", background: "radial-gradient(circle, rgba(236, 72, 153, 0.04) 0%, rgba(0,0,0,0) 70%)", top: "40%", right: "5%", borderRadius: "50%", filter: "blur(80px)", pointerEvents: "none" }} />
        </>
      )}

      {/* Header element */}
      <header className="border-bottom-thin" style={{ position: "sticky", top: 0, zIndex: 100, backdropFilter: "blur(12px)", background: isDark ? "rgba(9, 10, 15, 0.8)" : "rgba(250, 250, 250, 0.8)" }}>
        <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "14px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          
          <Logo size={32} rounded />
          
          <Space size={8}>
            <Button type="text" className="minimal-btn minimal-btn-text" onClick={() => setDocsOpen(true)}>
              Features
            </Button>
            <Button type="text" className="minimal-btn minimal-btn-text" onClick={() => setDocsOpen(true)}>
              Methodology
            </Button>
            
            <Tooltip title={`Switch to ${isDark ? "Light" : "Dark"} Mode`}>
              <Button
                type="text"
                className="minimal-btn minimal-btn-text"
                onClick={() => setMode(isDark ? "light" : "dark")}
                icon={isDark ? <SunOutlined style={{ color: "#faad14" }} /> : <MoonOutlined style={{ color: "#4f46e5" }} />}
              />
            </Tooltip>

            <Divider type="vertical" style={{ borderColor: isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0,0,0,0.1)", height: "20px" }} />

            {isLoggedIn ? (
              <Button
                type="primary"
                className="minimal-btn minimal-btn-primary"
                icon={<DashboardOutlined />}
                onClick={() => navigate("/dashboard")}
              >
                Dashboard
              </Button>
            ) : (
              <>
                <Button type="text" className="minimal-btn minimal-btn-text" onClick={() => navigate("/login")}>
                  Log in
                </Button>
                <Button
                  type="primary"
                  className="minimal-btn minimal-btn-primary"
                  onClick={() => navigate("/register")}
                >
                  Sign up
                </Button>
              </>
            )}
          </Space>

        </div>
      </header>

      {/* Hero Block Container */}
      <section className="section-container" style={{ textAlign: "center", paddingTop: "120px", paddingBottom: "60px" }}>
        
        {/* Release Pill Badge */}
        <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.04)", padding: "4px 12px", borderRadius: "100px", marginBottom: "28px", border: `1px solid ${isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)"}` }}>
          <Text style={{ fontSize: "11px", fontWeight: 600, color: "#3b82f6", textTransform: "uppercase", letterSpacing: "0.5px" }}>Release</Text>
          <div style={{ width: "4px", height: "4px", background: isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)", borderRadius: "50%" }}></div>
          <Text style={{ fontSize: "11px", fontWeight: 500, color: isDark ? "#94a3b8" : "#475569" }}>v1.0 is officially live</Text>
        </div>

        <Title
          level={1}
          className="gradient-headline"
          style={{
            fontSize: "64px",
            lineHeight: "1.1",
            fontWeight: 800,
            margin: "0 0 24px 0",
            letterSpacing: "-2px"
          }}
        >
          Continuous Quality Assuring <br />
          For Conversational Voice AI
        </Title>

        <Paragraph
          style={{
            fontSize: "19px",
            color: isDark ? "#94a3b8" : "#475569",
            maxWidth: "680px",
            margin: "0 auto 40px auto",
            lineHeight: "1.6",
            fontWeight: 400
          }}
        >
          Evaluate network lag, speech intelligibility, acoustic distortion, and turn-taking friction. Plug in your key provider configurations to view telemetry stream analysis automatically.
        </Paragraph>

        <Space size={12}>
          {isLoggedIn ? (
            <Button
              type="primary"
              size="large"
              className="minimal-btn minimal-btn-primary"
              style={{ height: "46px", padding: "0 28px", fontSize: "14px", fontWeight: 600 }}
              onClick={() => navigate("/dashboard")}
            >
              Go to Dashboard
            </Button>
          ) : (
            <>
              <Button
                type="primary"
                size="large"
                className="minimal-btn minimal-btn-primary"
                style={{ height: "46px", padding: "0 28px", fontSize: "14px", fontWeight: 600 }}
                onClick={() => navigate("/register")}
              >
                Start monitoring
              </Button>
              <Button
                size="large"
                className="minimal-btn minimal-btn-text"
                style={{ height: "46px", padding: "0 28px", border: `1px solid ${isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.15)"}` }}
                onClick={() => setDocsOpen(true)}
              >
                Read documentation
              </Button>
            </>
          )}
        </Space>

        {/* CSS Minimal Graphical Card Mockup */}
        <div className="grid-visual">
          {/* Simulated grid lines */}
          {Array.from({ length: 15 }).map((_, i) => (
            <div key={`h-${i}`} className="grid-line" style={{ left: 0, right: 0, top: `${i * 25}px`, height: "1px" }} />
          ))}
          {Array.from({ length: 25 }).map((_, i) => (
            <div key={`v-${i}`} className="grid-line" style={{ top: 0, bottom: 0, left: `${i * 50}px`, width: "1px" }} />
          ))}

          {/* Interactive Floating Card simulating telemetry */}
          <div
            style={{
              position: "absolute",
              top: "40px",
              left: "40px",
              background: isDark ? "rgba(17, 19, 30, 0.85)" : "rgba(255, 255, 255, 0.85)",
              border: `1px solid ${isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.08)"}`,
              borderRadius: "12px",
              padding: "20px",
              textAlign: "left",
              width: "280px",
              boxShadow: "0 10px 40px rgba(0,0,0,0.15)",
              backdropFilter: "blur(8px)"
            }}
          >
            <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "14px" }}>
              <div style={{ width: "8px", height: "8px", background: "#10b981", borderRadius: "50%", animation: "pulse 2s infinite" }}></div>
              <Text strong style={{ fontSize: "12px", color: isDark ? "#fff" : "#0f172a" }}>TELEMETRY STREAM CONNECTED</Text>
            </div>
            
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <div>
                <Text type="secondary" style={{ fontSize: "10px", display: "block" }}>AVG LATENCY</Text>
                <Text strong style={{ fontSize: "18px", color: "#3b82f6" }}>842ms</Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: "10px", display: "block" }}>NISQA</Text>
                <Text strong style={{ fontSize: "18px", color: "#10b981" }}>4.35 MOS</Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: "10px", display: "block" }}>DEAD AIR</Text>
                <Text strong style={{ fontSize: "18px", color: "#ef4444" }}>4.2%</Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: "10px", display: "block" }}>INTERRUPTIONS</Text>
                <Text strong style={{ fontSize: "18px", color: "#faad14" }}>3.1%</Text>
              </div>
            </div>
          </div>

          {/* Graphical vector representation of voice wave */}
          <div style={{ position: "absolute", bottom: "40px", right: "40px", width: "400px", height: "120px" }}>
            <svg viewBox="0 0 400 120" style={{ width: "100%", height: "100%" }}>
              <path
                d="M 10 60 Q 50 10, 80 80 T 150 40 T 230 110 T 300 20 T 350 70 T 390 60"
                fill="none"
                stroke="url(#gradient-line)"
                strokeWidth="4"
                strokeLinecap="round"
              />
              <defs>
                <linearGradient id="gradient-line" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#3b82f6" />
                  <stop offset="50%" stopColor="#8b5cf6" />
                  <stop offset="100%" stopColor="#ec4899" />
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>

      </section>

      {/* The Problem Section */}
      <section className="border-bottom-thin" style={{ background: isDark ? "#0c0d15" : "#fbfbfb" }}>
        <div className="section-container" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "60px", alignItems: "center" }}>
          <div>
            <Text style={{ color: "#3b82f6", fontWeight: 600, fontSize: "13px", letterSpacing: "1px", textTransform: "uppercase" }}>The Problem</Text>
            <Title level={2} style={{ fontSize: "36px", marginTop: "12px", color: isDark ? "#fff" : "#1e293b", fontWeight: 700 }}>
              Evaluating Voice Agents <br /> Is Not Simple Text
            </Title>
            <Paragraph style={{ color: isDark ? "#94a3b8" : "#475569", fontSize: "15px", lineHeight: "1.6", marginTop: "16px" }}>
              Unlike textual LLMs that wait for complete outputs, voice agents interact in milliseconds. Measuring transcription accuracy fails to capture acoustic dropouts, turn interruption friction, model responsiveness, and speech alignment quality.
            </Paragraph>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div style={{ display: "flex", gap: "16px" }}>
              <div style={{ color: "#ef4444", fontSize: "20px", fontWeight: "bold" }}>01</div>
              <div>
                <Text strong style={{ color: isDark ? "#fff" : "#0f172a", fontSize: "15px" }}>The Silence Dilemma</Text>
                <Paragraph style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "13px", margin: 0, marginTop: "4px" }}>
                  Long silences (dead air) degrade caller retention and indicate server connectivity timeouts or prompt delay glitches.
                </Paragraph>
              </div>
            </div>

            <div style={{ display: "flex", gap: "16px" }}>
              <div style={{ color: "#ef4444", fontSize: "20px", fontWeight: "bold" }}>02</div>
              <div>
                <Text strong style={{ color: isDark ? "#fff" : "#0f172a", fontSize: "15px" }}>Interruptive Overlaps</Text>
                <Paragraph style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "13px", margin: 0, marginTop: "4px" }}>
                  Excessive crosstalk occurs when voice activation thresholds trigger too quickly, causing agent speech collisions.
                </Paragraph>
              </div>
            </div>

            <div style={{ display: "flex", gap: "16px" }}>
              <div style={{ color: "#ef4444", fontSize: "20px", fontWeight: "bold" }}>03</div>
              <div>
                <Text strong style={{ color: isDark ? "#fff" : "#0f172a", fontSize: "15px" }}>Acoustic Jitter & Color</Text>
                <Paragraph style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "13px", margin: 0, marginTop: "4px" }}>
                  Poor audio quality degrades voice recognition. Benten monitors NISQA score values objectively without intrusive setups.
                </Paragraph>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Methodology Pipeline */}
      <section className="section-container" style={{ textAlign: "center" }}>
        <Text style={{ color: "#3b82f6", fontWeight: 600, fontSize: "13px", letterSpacing: "1px", textTransform: "uppercase" }}>Methodology</Text>
        <Title level={2} style={{ fontSize: "36px", marginTop: "12px", color: isDark ? "#fff" : "#1e293b", fontWeight: 700, marginBottom: "64px" }}>
          How Benten Computes Metrics
        </Title>

        <Row gutter={[32, 32]}>
          <Col xs={24} md={8}>
            <div style={{ padding: "0 16px" }}>
              <div style={{ display: "inline-flex", width: "48px", height: "48px", background: "rgba(139, 92, 246, 0.1)", borderRadius: "50%", justifyContent: "center", alignItems: "center", marginBottom: "20px", color: "#8b5cf6", fontSize: "20px", fontWeight: "bold" }}>1</div>
              <Title level={4} style={{ fontSize: "18px", color: isDark ? "#fff" : "#1e293b", fontWeight: 600, marginBottom: "10px" }}>Ingest Webhooks</Title>
              <Paragraph style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "14px", lineHeight: "1.5" }}>
                Connect Vapi or Retell APIs. Benten registers webhook listeners to inspect real-time stream completion alerts automatically.
              </Paragraph>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <div style={{ padding: "0 16px" }}>
              <div style={{ display: "inline-flex", width: "48px", height: "48px", background: "rgba(16, 185, 129, 0.1)", borderRadius: "50%", justifyContent: "center", alignItems: "center", marginBottom: "20px", color: "#10b981", fontSize: "20px", fontWeight: "bold" }}>2</div>
              <Title level={4} style={{ fontSize: "18px", color: isDark ? "#fff" : "#1e293b", fontWeight: 600, marginBottom: "10px" }}>ML Processing</Title>
              <Paragraph style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "14px", lineHeight: "1.5" }}>
                Celery pipelines trigger acoustic model checks: checking voice quality (NISQA model) and speaker turn-taking gaps.
              </Paragraph>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <div style={{ padding: "0 16px" }}>
              <div style={{ display: "inline-flex", width: "48px", height: "48px", background: "rgba(59, 130, 246, 0.1)", borderRadius: "50%", justifyContent: "center", alignItems: "center", marginBottom: "20px", color: "#3b82f6", fontSize: "20px", fontWeight: "bold" }}>3</div>
              <Title level={4} style={{ fontSize: "18px", color: isDark ? "#fff" : "#1e293b", fontWeight: 600, marginBottom: "10px" }}>Inspect Results</Title>
              <Paragraph style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "14px", lineHeight: "1.5" }}>
                Telemetry logs register to your dashboard. Filter caller anomalies and export health diagnostics logs instantly.
              </Paragraph>
            </div>
          </Col>
        </Row>
      </section>

      {/* Feature grid breakdown */}
      <section className="border-bottom-thin" style={{ background: isDark ? "#0c0d15" : "#fbfbfb" }}>
        <div className="section-container">
          <div style={{ textAlign: "center", marginBottom: "64px" }}>
            <Text style={{ color: "#3b82f6", fontWeight: 600, fontSize: "13px", letterSpacing: "1px", textTransform: "uppercase" }}>Features</Text>
            <Title level={2} style={{ fontSize: "36px", marginTop: "12px", color: isDark ? "#fff" : "#1e293b", fontWeight: 700 }}>
              Tailored Telemetry Blocks
            </Title>
          </div>

          <Row gutter={[24, 24]}>
            {features.map((feat, index) => (
              <Col xs={24} sm={12} key={index}>
                <Card bordered={false} className="minimal-card" styles={{ body: { padding: "32px" } }}>
                  <div style={{ display: "flex", gap: "20px", alignItems: "flex-start" }}>
                    <div style={{ padding: "10px", borderRadius: "8px", background: isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)" }}>
                      {feat.icon}
                    </div>
                    <div>
                      <Title level={4} style={{ color: isDark ? "#fff" : "#0f172a", margin: "0 0 8px 0", fontSize: "16px", fontWeight: 600 }}>
                        {feat.title}
                      </Title>
                      <Paragraph style={{ color: isDark ? "#64748b" : "#475569", margin: 0, fontSize: "14px", lineHeight: "1.5" }}>
                        {feat.description}
                      </Paragraph>
                    </div>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      </section>

      {/* Support Providers */}
      <section className="section-container" style={{ textAlign: "center" }}>
        <Text style={{ color: "#3b82f6", fontWeight: 600, fontSize: "13px", letterSpacing: "1px", textTransform: "uppercase" }}>Integrations</Text>
        <Title level={2} style={{ fontSize: "36px", marginTop: "12px", color: isDark ? "#fff" : "#1e293b", fontWeight: 700, marginBottom: "48px" }}>
          Synced Voice Connectors out-of-the-box
        </Title>

        <Row gutter={[20, 20]}>
          {providers.map((prov, i) => (
            <Col xs={24} sm={12} md={6} key={i}>
              <Card
                bordered={false}
                style={{
                  background: isDark ? "#11131e" : "#ffffff",
                  border: `1px solid ${isDark ? "rgba(255,255,255,0.04)" : "rgba(0, 0, 0, 0.06)"}`,
                  borderRadius: "10px",
                  textAlign: "center"
                }}
                bodyStyle={{ padding: "24px 20px" }}
              >
                <div style={{ width: "8px", height: "8px", background: prov.color, borderRadius: "50%", margin: "0 auto 12px auto" }} />
                <Title level={4} style={{ color: isDark ? "#fff" : "#0f172a", fontSize: "16px", fontWeight: 600, margin: "0 0 6px 0" }}>
                  {prov.name}
                </Title>
                <Text style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "12px" }}>
                  {prov.desc}
                </Text>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* Bottom CTA Element */}
      <section className="border-bottom-thin" style={{ background: isDark ? "#0c0d15" : "#f6f6f6", textAlign: "center" }}>
        <div className="section-container" style={{ padding: "100px 24px" }}>
          <Title level={2} style={{ fontSize: "40px", color: isDark ? "#fff" : "#0f172a", fontWeight: 700, marginBottom: "16px" }}>
            Ready to Assure Your Voice Agents?
          </Title>
          <Paragraph style={{ color: isDark ? "#64748b" : "#475569", fontSize: "16px", maxWidth: "600px", margin: "0 auto 36px auto" }}>
            Set up workspace projects, plug in credentials, and access detailed incident reports. Get started for free.
          </Paragraph>

          <Space size={14}>
            {isLoggedIn ? (
              <Button
                type="primary"
                size="large"
                className="minimal-btn minimal-btn-primary"
                style={{ height: "46px", padding: "0 32px", fontSize: "14px", fontWeight: 600 }}
                onClick={() => navigate("/dashboard")}
              >
                Return to Command Center
              </Button>
            ) : (
              <>
                <Button
                  type="primary"
                  size="large"
                  className="minimal-btn minimal-btn-primary"
                  style={{ height: "46px", padding: "0 32px", fontSize: "14px", fontWeight: 600 }}
                  onClick={() => navigate("/register")}
                >
                  Create Your Account
                </Button>
                <Button
                  size="large"
                  className="minimal-btn minimal-btn-text"
                  style={{ height: "46px", padding: "0 28px", border: `1px solid ${isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.15)"}` }}
                  onClick={() => setDocsOpen(true)}
                >
                  Read documentation
                </Button>
              </>
            )}
          </Space>
        </div>
      </section>

      {/* Footer Area */}
      <footer style={{ background: isDark ? "#090a0f" : "#fafafa", padding: "60px 24px 40px 24px" }}>
        <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
          <Row gutter={[40, 40]}>
            <Col xs={24} md={10}>
              <Logo size={28} />
              <Paragraph style={{ color: isDark ? "#64748b" : "#64748b", marginTop: "16px", fontSize: "13px", maxWidth: "300px", lineHeight: "1.6" }}>
                Benten performs real-time acoustic evaluations of conversational speech models under your control.
              </Paragraph>
              <div style={{ display: "flex", gap: "16px", marginTop: "24px" }}>
                <a href="#github" style={{ color: isDark ? "#94a3b8" : "#475569" }}><GithubOutlined style={{ fontSize: "18px" }} /></a>
              </div>
            </Col>

            <Col xs={12} md={7}>
              <Title level={5} style={{ color: isDark ? "#fff" : "#0f172a", fontSize: "13px", fontWeight: 600, marginBottom: "16px", textTransform: "uppercase", letterSpacing: "0.5px" }}>Product</Title>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <a href="#features" onClick={() => setDocsOpen(true)} style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "13px" }}>Acoustic NISQA</a>
                <a href="#latency" onClick={() => setDocsOpen(true)} style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "13px" }}>Latency Stream</a>
                <a href="#dashboard" onClick={() => setDocsOpen(true)} style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "13px" }}>Command Center</a>
              </div>
            </Col>

            <Col xs={12} md={7}>
              <Title level={5} style={{ color: isDark ? "#fff" : "#0f172a", fontSize: "13px", fontWeight: 600, marginBottom: "16px", textTransform: "uppercase", letterSpacing: "0.5px" }}>Resources</Title>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <a href="#docs" onClick={() => setDocsOpen(true)} style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "13px" }}>Documentation</a>
                <a href="#changelog" onClick={() => setDocsOpen(true)} style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "13px" }}>Changelog</a>
                <a href="#status" onClick={() => setDocsOpen(true)} style={{ color: isDark ? "#64748b" : "#64748b", fontSize: "13px" }}>Status logs</a>
              </div>
            </Col>
          </Row>

          <Divider style={{ borderColor: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)", margin: "40px 0 20px 0" }} />
          
          <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
            <Text style={{ color: isDark ? "#475569" : "#94a3b8", fontSize: "12px" }}>&copy; {new Date().getFullYear()} Benten. All rights reserved.</Text>
            <Text style={{ color: isDark ? "#475569" : "#94a3b8", fontSize: "12px" }}>Autonomous AI Voice Agent Scorer</Text>
          </div>
        </div>
      </footer>

      {/* Docs Drawer */}
      <Drawer
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Logo size={24} />
            <Text strong style={{ color: isDark ? "#fff" : "#0f172a", fontSize: 16 }}>Documentation</Text>
          </div>
        }
        placement="right"
        width={500}
        onClose={() => setDocsOpen(false)}
        open={docsOpen}
        styles={{
          header: {
            background: isDark ? "#11131e" : "#ffffff",
            borderBottom: `1px solid ${isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)"}`
          },
          body: {
            background: isDark ? "#11131e" : "#ffffff",
            color: isDark ? "#fff" : "#334155"
          }
        }}
      >
        <Space direction="vertical" size={24} style={{ width: "100%" }}>
          <div>
            <Title level={4} style={{ color: isDark ? "#fff" : "#0f172a", marginBottom: 12 }}>What is Benten?</Title>
            <Paragraph style={{ color: isDark ? "rgba(255,255,255,0.6)" : "#475569" }}>
              Benten is a specialized audio performance and evaluation command center. It operates as a non-intrusive analyzer that evaluates recordings directly from voice connector APIs.
            </Paragraph>
          </div>

          <div>
            <Title level={4} style={{ color: isDark ? "#fff" : "#0f172a", marginBottom: 12 }}>Evaluation Metrics</Title>
            <Space direction="vertical" size={14} style={{ width: "100%" }}>
              <div>
                <Text strong style={{ color: isDark ? "#fff" : "#0f172a" }}>NISQA Speech Quality (MOS):</Text>
                <Paragraph style={{ color: isDark ? "rgba(255,255,255,0.6)" : "#475569", margin: 0 }}>
                  A Deep Learning model trained to predict voice quality score from 1 (poor) to 5 (excellent). Analyzes noise, coloration, and distortion.
                </Paragraph>
              </div>
              <div>
                <Text strong style={{ color: isDark ? "#fff" : "#0f172a" }}>Dead Air Check:</Text>
                <Paragraph style={{ color: isDark ? "rgba(255,255,255,0.6)" : "#475569", margin: 0 }}>
                  Calculates total silence duration ratio. Excessive silence denotes latency issues or agent hang-up anomalies.
                </Paragraph>
              </div>
              <div>
                <Text strong style={{ color: isDark ? "#fff" : "#0f172a" }}>Turn Latency:</Text>
                <Paragraph style={{ color: isDark ? "rgba(255,255,255,0.6)" : "#475569", margin: 0 }}>
                  Tracks the time (in milliseconds) from user finishing speech to the voice agent reacting back.
                </Paragraph>
              </div>
            </Space>
          </div>

          <div>
            <Title level={4} style={{ color: isDark ? "#fff" : "#0f172a", marginBottom: 12 }}>Getting Started</Title>
            <Paragraph style={{ color: isDark ? "rgba(255,255,255,0.6)" : "#475569" }}>
              1. Sign up/create a Workspace Project <br />
              2. Go to Integrations inside Dashboard <br />
              3. Connect your API key (e.g. Vapi or Retell) <br />
              4. Click Sync Agents. All agents automatically pull and sync telemetry into dashboards!
            </Paragraph>
          </div>
        </Space>
      </Drawer>
    </div>
  );
};
