import React, { useState } from "react";
import { Card, Tabs, Form, Input, Button, Switch, Select, Table, Typography, Space, Tag, InputNumber } from "antd";
import { SettingOutlined, DatabaseOutlined, SaveOutlined, SecurityScanOutlined, FileProtectOutlined } from "@ant-design/icons";

const { Title, Text, Paragraph } = Typography;

export const SettingsList: React.FC = () => {
  const [retentionDays, setRetentionDays] = useState(30);
  const [retentionEnabled, setRetentionEnabled] = useState(true);

  // Mock Audit Logs
  const auditLogs = [
    { key: "1", time: "2026-07-18 11:15", user: "Ayush Ranjan", action: "Updated Vapi credentials", ip: "192.168.1.14" },
    { key: "2", time: "2026-07-18 09:30", user: "Sarah Connor", action: "Triggered High Latency alert rule", ip: "10.0.4.15" },
    { key: "3", time: "2026-07-17 17:45", user: "Ayush Ranjan", action: "Invited John Doe", ip: "192.168.1.14" },
  ];

  const auditColumns = [
    { title: "Timestamp", dataIndex: "time", key: "time" },
    { title: "User Profile", dataIndex: "user", key: "user" },
    { title: "Action Performed", dataIndex: "action", key: "action" },
    { title: "Client IP Address", dataIndex: "ip", key: "ip" },
  ];

  return (
    <div style={{ padding: "4px" }}>
      <div style={{ marginBottom: "20px" }}>
        <Title level={2} style={{ margin: 0 }}>System Administration</Title>
        <Text type="secondary">Admin panel to configure hosting paths, retention, scheduling backups, and monitoring audit logs.</Text>
      </div>

      <Card bordered={false}>
        <Tabs
          defaultActiveKey="1"
          items={[
            {
              key: "1",
              label: (
                <span>
                  <SettingOutlined />
                  General & Self-Hosting
                </span>
              ),
              children: (
                <div style={{ padding: "10px 0" }}>
                  <Title level={4}>Self-Hosting Configurations</Title>
                  <Paragraph type="secondary">Configure local mount paths for call storage and local processing databases.</Paragraph>
                  <Form layout="vertical" style={{ maxWidth: 600 }}>
                    <Form.Item label="Storage Directory Path" initialValue="/var/lib/benten/recordings">
                      <Input placeholder="/var/lib/benten/recordings" />
                    </Form.Item>
                    <Form.Item label="API Bind Address" initialValue="0.0.0.0:8080">
                      <Input placeholder="0.0.0.0:8080" />
                    </Form.Item>
                    <Form.Item label="External Domain URL" initialValue="https://voiceops.mycompany.com">
                      <Input placeholder="https://voiceops.mycompany.com" />
                    </Form.Item>
                    <Button type="primary" icon={<SaveOutlined />}>Save Base Configuration</Button>
                  </Form>
                </div>
              ),
            },
            {
              key: "2",
              label: (
                <span>
                  <DatabaseOutlined />
                  Data Retention & Policy
                </span>
              ),
              children: (
                <div style={{ padding: "10px 0" }}>
                  <Title level={4}>Audio & Evaluation Log Retention</Title>
                  <Paragraph type="secondary">Define automatic database scrubbing intervals to stay compliant with local storage limitations.</Paragraph>
                  <Space direction="vertical" size="large" style={{ width: "100%" }}>
                    <Space size="middle">
                      <Switch checked={retentionEnabled} onChange={setRetentionEnabled} />
                      <Text strong>Enable Automated Log Purging</Text>
                    </Space>

                    {retentionEnabled && (
                      <div>
                        <Text style={{ display: "block", marginBottom: "8px" }}>Remove records and audio playbacks older than:</Text>
                        <Space>
                          <InputNumber min={1} max={365} value={retentionDays} onChange={(val) => setRetentionDays(val || 30)} />
                          <Text>days</Text>
                        </Space>
                      </div>
                    )}
                    <Button type="primary" icon={<SaveOutlined />}>Save Purge Policy</Button>
                  </Space>
                </div>
              ),
            },
            {
              key: "3",
              label: (
                <span>
                  <SaveOutlined />
                  Backup & Schedulers
                </span>
              ),
              children: (
                <div style={{ padding: "10px 0" }}>
                  <Title level={4}>Scheduled Backups</Title>
                  <Paragraph type="secondary">Export database configurations and evaluation metrics metadata to an S3 compatible storage buckets.</Paragraph>
                  <Form layout="vertical" style={{ maxWidth: 600 }}>
                    <Form.Item label="Backup Target Service" initialValue="aws-s3">
                      <Select
                        options={[
                          { value: "aws-s3", label: "Amazon S3 Bucket" },
                          { value: "gcs", label: "Google Cloud Storage" },
                          { value: "local", label: "Local Archive Mount" },
                        ]}
                      />
                    </Form.Item>
                    <Form.Item label="Destination Bucket Name" initialValue="benten-backups-prod">
                      <Input placeholder="benten-backups-prod" />
                    </Form.Item>
                    <Form.Item label="Scheduling Interval" initialValue="daily">
                      <Select
                        options={[
                          { value: "hourly", label: "Hourly" },
                          { value: "daily", label: "Daily at Midnight" },
                          { value: "weekly", label: "Weekly on Sundays" },
                        ]}
                      />
                    </Form.Item>
                    <Button type="primary" icon={<SaveOutlined />}>Save Backup Schedule</Button>
                  </Form>
                </div>
              ),
            },
            {
              key: "4",
              label: (
                <span>
                  <FileProtectOutlined />
                  Licensing & Billing
                </span>
              ),
              children: (
                <div style={{ padding: "10px 0" }}>
                  <Title level={4}>License Information</Title>
                  <Paragraph type="secondary">Monitor current software boundaries and license validation status.</Paragraph>
                  <Card style={{ background: "rgba(82, 196, 26, 0.05)", border: "1px solid #b7eb8f" }}>
                    <Space direction="vertical">
                      <Space>
                        <Tag color="success">✓ LICENSED</Tag>
                        <Text strong>VoiceOps Enterprise License Key</Text>
                      </Space>
                      <Text code>VOICEOPS-ENT-99A1-BB23-FF44-XXXX</Text>
                      <Text type="secondary" style={{ fontSize: "12px" }}>Expires on July 1, 2027 (Active for 363 days)</Text>
                    </Space>
                  </Card>
                </div>
              ),
            },
            {
              key: "5",
              label: (
                <span>
                  <SecurityScanOutlined />
                  Security Audit Logs
                </span>
              ),
              children: (
                <div style={{ padding: "10px 0" }}>
                  <Title level={4}>Audit Log Logs</Title>
                  <Paragraph type="secondary">Track administrative and configuration changes made across your organization team workspaces.</Paragraph>
                  <Table dataSource={auditLogs} columns={auditColumns} pagination={false} bordered size="small" />
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

// Activity: simulated update on 2026-04-02

// Activity: simulated update on 2026-04-21

// Activity: simulated update on 2026-04-23

// Activity: simulated update on 2026-05-29

// Activity: simulated update on 2026-06-04
