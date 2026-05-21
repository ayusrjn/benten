export interface Project {
  id: string;
  name: string;
  agentsCount: number;
  conversationsCount: number;
  avgHealth: number;
}

export interface Agent {
  id: string;
  projectId: string;
  name: string;
  provider: string;
  conversationsCount: number;
  healthScore: number;
  latencyTrend: number[];
  deadAirTrend: number[];
  interruptionsTrend: number[];
  emotionTrend: number[];
  topProblems: string[];
}

export interface SpeechSegment {
  speaker: "user" | "agent";
  start: number; // in seconds
  end: number; // in seconds
  text: string;
}

export interface Conversation {
  id: string;
  agentId: string;
  agentName: string;
  projectId: string;
  score: number;
  duration: string; // e.g. "4m"
  durationSec: number; // e.g. 240
  status: "Healthy" | "Warning" | "Critical";
  date: string;
  latencyMs: number;
  interruptions: number;
  deadAirPercent: number;
  speechRateWpm: number;
  emotion: string;
  voiceQuality: number;
  emotionTimeline: string[]; // e.g. ["😀", "😀", "😐", "😐", "😐", "😞", "😞", "😀"]
  detectedIssues: string[];
  segments: SpeechSegment[];
  rawMetrics: object;
}

export interface Alert {
  id: string;
  name: string;
  status: "Triggered" | "Recovered";
  agentName: string;
  timeText: string;
  metric: string;
}

export interface AlertRule {
  id: string;
  metric: string;
  threshold: string;
  duration: string;
  action: string;
}

export interface Integration {
  id: string;
  name: string;
  connected: boolean;
  apiKey: string;
  webhookUrl?: string;
}

export interface Member {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar: string;
}

// -------------------------------------------------------------
// SEED MOCK DATA
// -------------------------------------------------------------

export const mockProjects: Project[] = [
  { id: "proj-a", name: "Project A (Customer Support & Sales)", agentsCount: 2, conversationsCount: 19423, avgHealth: 88 },
  { id: "proj-b", name: "Project B (Reception & Clinic)", agentsCount: 2, conversationsCount: 4631, avgHealth: 90 },
];

export const mockAgents: Agent[] = [
  {
    id: "agent-sales",
    projectId: "proj-a",
    name: "Sales Agent",
    provider: "ElevenLabs",
    conversationsCount: 12301,
    healthScore: 95,
    latencyTrend: [480, 460, 440, 420, 410, 405, 410],
    deadAirTrend: [4.2, 4.0, 3.8, 3.5, 3.2, 3.0, 3.2],
    interruptionsTrend: [12, 10, 8, 9, 7, 6, 8],
    emotionTrend: [85, 88, 90, 92, 94, 95, 94],
    topProblems: ["Tool timeout during CRM lookup", "Slow TTS response under heavy load", "User barge-ins on greeting"],
  },
  {
    id: "agent-support",
    projectId: "proj-a",
    name: "Support Agent",
    provider: "Vapi",
    conversationsCount: 7122,
    healthScore: 81,
    latencyTrend: [750, 780, 810, 850, 920, 950, 980],
    deadAirTrend: [8.5, 9.0, 9.8, 10.5, 11.2, 12.0, 11.5],
    interruptionsTrend: [22, 24, 28, 31, 35, 38, 36],
    emotionTrend: [70, 68, 65, 62, 60, 58, 63],
    topProblems: ["Vapi Webhook Latency > 1.5s", "Dead air increased by 14% after system update", "Frequent interruptions during checkout assistance"],
  },
  {
    id: "agent-receptionist",
    projectId: "proj-b",
    name: "Receptionist Agent",
    provider: "Retell",
    conversationsCount: 3210,
    healthScore: 88,
    latencyTrend: [380, 390, 400, 410, 390, 400, 395],
    deadAirTrend: [2.5, 2.8, 3.0, 3.1, 2.9, 3.0, 2.8],
    interruptionsTrend: [5, 6, 7, 5, 4, 6, 5],
    emotionTrend: [90, 91, 92, 90, 92, 93, 92],
    topProblems: ["Calendar API sync delay", "Volume drop on long calls"],
  },
  {
    id: "agent-clinic",
    projectId: "proj-b",
    name: "Clinic Agent",
    provider: "OpenAI Realtime",
    conversationsCount: 1421,
    healthScore: 92,
    latencyTrend: [320, 310, 300, 290, 280, 270, 260],
    deadAirTrend: [1.8, 1.7, 1.6, 1.5, 1.4, 1.3, 1.2],
    interruptionsTrend: [3, 2, 2, 3, 2, 1, 1],
    emotionTrend: [94, 95, 96, 95, 96, 97, 96],
    topProblems: ["Medical terminology phoneme mapping", "Brief silence after medication lists"],
  },
];

export const mockConversations: Conversation[] = [
  {
    id: "A1B2",
    agentId: "agent-sales",
    agentName: "Sales Agent",
    projectId: "proj-a",
    score: 91,
    duration: "4m",
    durationSec: 240,
    status: "Healthy",
    date: "2026-07-18 10:15",
    latencyMs: 410,
    interruptions: 2,
    deadAirPercent: 3,
    speechRateWpm: 162,
    emotion: "Calm",
    voiceQuality: 94,
    emotionTimeline: ["😀", "😀", "😐", "😐", "😐", "😞", "😞", "😀"],
    detectedIssues: ["User interrupted agent twice during greeting", "Long silence (1.8s) after custom tool database call", "Volume dropped towards the end of the call"],
    segments: [
      { speaker: "agent", start: 0, end: 4, text: "Hello! Welcome to VoiceCorp. Thank you for calling. How can I help you today?" },
      { speaker: "user", start: 4, end: 8, text: "Hi, I received an email about a subscription discount, is that still active?" },
      { speaker: "agent", start: 9, end: 16, text: "Yes, definitely! Let me check the details for you. I am looking up our current promotions..." },
      { speaker: "user", start: 15, end: 20, text: "Great. It was for the premium plan." },
      { speaker: "agent", start: 21, end: 27, text: "Perfect. Yes, I see the 20% discount is valid until the end of the month. Shall we apply it?" },
      { speaker: "user", start: 28, end: 30, text: "Yes please, let's do it." },
      { speaker: "agent", start: 31, end: 38, text: "Done! Your plan has been upgraded. You'll receive a confirmation email shortly." },
    ],
    rawMetrics: {
      audio_quality: { mos: 4.4, snr_db: 32.1, jitter_ms: 2.1 },
      timing: { agent_speech_duration: 154, user_speech_duration: 72, silence_duration: 14 },
      stt: { confidence: 0.985, latency_p90_ms: 120 },
      tts: { latency_p90_ms: 280 },
      llm: { latency_p90_ms: 80 },
    },
  },
  {
    id: "A1B3",
    agentId: "agent-support",
    agentName: "Support Agent",
    projectId: "proj-a",
    score: 63,
    duration: "9m",
    durationSec: 540,
    status: "Warning",
    date: "2026-07-18 09:30",
    latencyMs: 1200,
    interruptions: 5,
    deadAirPercent: 11,
    speechRateWpm: 140,
    emotion: "Frustrated",
    voiceQuality: 78,
    emotionTimeline: ["😐", "😐", "😞", "😞", "😡", "😡", "😞", "😐"],
    detectedIssues: ["Average latency exceeded 1.2s", "Dead air exceeded 10%", "User exhibited frustration markers twice", "Agent talked over user 3 times"],
    segments: [
      { speaker: "agent", start: 0, end: 3, text: "Hello, this is Support. How can I assist you with your portal issues?" },
      { speaker: "user", start: 4, end: 12, text: "I have been trying to log in for the last hour and it keeps throwing a 500 error code. I need this resolved immediately!" },
      { speaker: "agent", start: 14, end: 22, text: "I understand. Let me query the user profile logs... (silence)... Can you provide your registered email address?" },
      { speaker: "user", start: 21, end: 24, text: "It is john.doe@example.com." },
      { speaker: "agent", start: 26, end: 35, text: "Okay... searching database... please hold... (long silence)... Still searching... it seems to be taking longer than expected." },
      { speaker: "user", start: 34, end: 40, text: "Why is it taking so long? I am in a hurry." },
    ],
    rawMetrics: {
      audio_quality: { mos: 3.5, snr_db: 22.4, jitter_ms: 8.5 },
      timing: { agent_speech_duration: 310, user_speech_duration: 170, silence_duration: 60 },
      stt: { confidence: 0.91, latency_p90_ms: 250 },
      tts: { latency_p90_ms: 610 },
      llm: { latency_p90_ms: 340 },
    },
  },
  {
    id: "A1B4",
    agentId: "agent-clinic",
    agentName: "Clinic Agent",
    projectId: "proj-b",
    score: 84,
    duration: "6m",
    durationSec: 360,
    status: "Healthy",
    date: "2026-07-18 08:45",
    latencyMs: 520,
    interruptions: 1,
    deadAirPercent: 4,
    speechRateWpm: 155,
    emotion: "Neutral",
    voiceQuality: 88,
    emotionTimeline: ["😐", "😐", "😀", "😀", "😐", "😐", "😀", "😀"],
    detectedIssues: ["Slight audio jitter detected", "Short silence after medical database write query"],
    segments: [
      { speaker: "agent", start: 0, end: 4, text: "Good morning. You are speaking with the Clinic Assistant. How can I assist with your appointment?" },
      { speaker: "user", start: 5, end: 9, text: "Hi, I need to reschedule my dental checkup for next Thursday." },
      { speaker: "agent", start: 10, end: 17, text: "Certainly. Next Thursday is July 23rd. I have openings at 10 AM, 1 PM, and 3:30 PM. Which works?" },
      { speaker: "user", start: 18, end: 21, text: "1 PM works best for me." },
      { speaker: "agent", start: 22, end: 29, text: "Great. I have booked you for July 23rd at 1 PM. You will receive a text confirmation." },
    ],
    rawMetrics: {
      audio_quality: { mos: 4.1, snr_db: 28.5, jitter_ms: 4.2 },
      timing: { agent_speech_duration: 210, user_speech_duration: 130, silence_duration: 20 },
      stt: { confidence: 0.965, latency_p90_ms: 150 },
      tts: { latency_p90_ms: 290 },
      llm: { latency_p90_ms: 80 },
    },
  },
];

export const mockAlerts: Alert[] = [
  { id: "alert-1", name: "High Latency", status: "Triggered", agentName: "Sales Agent", timeText: "14 min ago", metric: "Average Latency > 1.2s" },
  { id: "alert-2", name: "Dead Air", status: "Triggered", agentName: "Support Agent", timeText: "2 hours ago", metric: "Dead Air > 10% for 5 min" },
  { id: "alert-3", name: "Emotion Stability", status: "Recovered", agentName: "Clinic Agent", timeText: "Yesterday", metric: "Frustration Indicators Detected" },
];

export const mockAlertRules: AlertRule[] = [
  { id: "rule-1", metric: "Dead Air", threshold: "> 10%", duration: "5 minutes", action: "Send Slack & PagerDuty" },
  { id: "rule-2", metric: "Average Latency", threshold: "> 2 seconds", duration: "3 minutes", action: "Send Email Notification" },
  { id: "rule-3", metric: "Interruptions Count", threshold: "> 5", duration: "1 conversation", action: "Flag in Dashboard" },
];

export const mockIntegrations: Integration[] = [
  { id: "elevenlabs", name: "ElevenLabs", connected: true, apiKey: "••••••••••••••••••••••••3a4b" },
  { id: "vapi", name: "Vapi", connected: true, apiKey: "••••••••••••••••••••••••8c9d", webhookUrl: "https://api.voicecorp.com/vapi-webhook" },
  { id: "retell", name: "Retell", connected: false, apiKey: "" },
  { id: "openai", name: "OpenAI Realtime API", connected: false, apiKey: "" },
];

export const mockMembers: Member[] = [
  { id: "u-1", name: "Ayush Ranjan", email: "ayush@voicecorp.com", role: "Owner / Admin", avatar: "https://i.pravatar.cc/150?img=33" },
  { id: "u-2", name: "Sarah Connor", email: "sarah@voicecorp.com", role: "Developer", avatar: "https://i.pravatar.cc/150?img=49" },
  { id: "u-3", name: "John Doe", email: "john@voicecorp.com", role: "Viewer", avatar: "https://i.pravatar.cc/150?img=12" },
];

export const mockOrgStats = {
  name: "VoiceCorp",
  membersCount: 12,
  projectsCount: 8,
  apiKeysCount: 3,
  storageUsedGb: 42,
  storageLimitGb: 100,
};

// Activity: simulated update on 2026-03-18

// Activity: simulated update on 2026-05-21
