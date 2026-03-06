import React, { useState } from "react";
import { Table, Tag, Button, Typography, Space, Modal, Form, Select, Input, Row, Col, Card, Timeline } from "antd";
import { AlertOutlined, PlusOutlined, SlackOutlined, MailOutlined, BellOutlined, CheckCircleOutlined, WarningOutlined } from "@ant-design/icons";
import { mockAlerts, mockAlertRules, AlertRule } from "../../providers/mockData";

const { Title, Text } = Typography;

export const AlertList: React.FC = () => {
  const [rules, setRules] = useState<AlertRule[]>(mockAlertRules);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();

  const handleCreateRule = (values: any) => {
    const newRule: AlertRule = {
      id: `rule-${rules.length + 1}`,
      metric: values.metric,
      threshold: values.threshold,
      duration: values.duration,
      action: values.action,
    };
    setRules([...rules, newRule]);
    setIsModalOpen(false);
    form.resetFields();
  };

  const columns = [
    {
      title: "Metric Rule",
      dataIndex: "metric",
      key: "metric",
      render: (text: string, record: AlertRule) => (
        <Text strong>{text} {record.threshold}</Text>
      ),
    },
    {
      title: "Duration Window",
      dataIndex: "duration",
      key: "duration",
    },
    {
      title: "Action Channels",
      dataIndex: "action",
      key: "action",
      render: (text: string) => {
        let icon = <BellOutlined />;
        if (text.includes("Slack")) icon = <SlackOutlined style={{ color: "#36C5F0" }} />;
        if (text.includes("Email")) icon = <MailOutlined style={{ color: "#1890ff" }} />;
        return (
          <Space>
            {icon}
            <Text>{text}</Text>
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: "4px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>Incident Alerting</Title>
          <Text type="secondary">Create threshold rules for voice latency, silence duration, or user sentiment to notify your engineering team.</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsModalOpen(true)}>
          Create Alert Rule
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        {/* Left Side: Active Incident Log */}
        <Col xs={24} lg={10}>
          <Card title={<Space><AlertOutlined style={{ color: "#ff4d4f" }} /><span>Active Alert Logs</span></Space>}>
            <Timeline
              items={mockAlerts.map((alert) => {
                const isTriggered = alert.status === "Triggered";
                return {
                  color: isTriggered ? "red" : "green",
                  dot: isTriggered ? <WarningOutlined style={{ fontSize: "16px" }} /> : <CheckCircleOutlined style={{ fontSize: "16px" }} />,
                  children: (
                    <div style={{ marginBottom: "10px" }}>
                      <Space>
                        <Text strong>{alert.name}</Text>
                        <Tag color={isTriggered ? "error" : "success"}>{alert.status.toUpperCase()}</Tag>
                      </Space>
                      <br />
                      <Text style={{ fontSize: "13px" }}>
                        Agent: <Text strong>{alert.agentName}</Text> | Metric: {alert.metric}
                      </Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: "11px" }}>{alert.timeText}</Text>
                    </div>
                  ),
                };
              })}
            />
          </Card>
        </Col>

        {/* Right Side: Alert Rules Table */}
        <Col xs={24} lg={14}>
          <Card title="Alerting Trigger Rules" style={{ height: "100%" }}>
            <Table
              dataSource={rules}
              columns={columns}
              rowKey="id"
              pagination={false}
              bordered
            />
          </Card>
        </Col>
      </Row>

      {/* Create Alert Rule Modal */}
      <Modal
        title="Configure Alert Trigger Rule"
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreateRule}>
          <Form.Item
            name="metric"
            label="Evaluation Metric"
            rules={[{ required: true, message: "Please select a metric" }]}
            initialValue="Average Latency"
          >
            <Select
              options={[
                { value: "Average Latency", label: "Average Latency" },
                { value: "Dead Air", label: "Dead Air Ratio" },
                { value: "Interruptions Count", label: "Interruptions Count" },
                { value: "Voice Quality MOS", label: "Voice Quality MOS" },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="threshold"
            label="Condition Threshold"
            rules={[{ required: true, message: "Please provide a threshold" }]}
          >
            <Input placeholder="e.g. > 10% or > 2 seconds" />
          </Form.Item>

          <Form.Item
            name="duration"
            label="Evaluation Window Duration"
            rules={[{ required: true, message: "Please provide a window duration" }]}
          >
            <Input placeholder="e.g. 5 minutes or 1 conversation" />
          </Form.Item>

          <Form.Item
            name="action"
            label="Notification Target"
            rules={[{ required: true, message: "Please select an action" }]}
            initialValue="Send Slack"
          >
            <Select
              options={[
                { value: "Send Slack & PagerDuty", label: "Send Slack & PagerDuty" },
                { value: "Send Email Notification", label: "Send Email Notification" },
                { value: "Flag in Dashboard", label: "Flag in Dashboard Only" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
