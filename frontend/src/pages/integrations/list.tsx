import React, { useState } from "react";
import { Row, Col, Card, Tag, Button, Typography, Space, Modal, Form, Input } from "antd";
import { ApiOutlined, CheckCircleOutlined, PlusOutlined, SettingOutlined } from "@ant-design/icons";
import { mockIntegrations, Integration } from "../../providers/mockData";

const { Title, Text, Paragraph } = Typography;

export const IntegrationList: React.FC = () => {
  const [integrations, setIntegrations] = useState<Integration[]>(mockIntegrations);
  const [activeIntegration, setActiveIntegration] = useState<Integration | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();

  const handleOpenConfig = (item: Integration) => {
    setActiveIntegration(item);
    setIsModalOpen(true);
    form.setFieldsValue({
      apiKey: item.apiKey,
      webhookUrl: item.webhookUrl || "",
    });
  };

  const handleSaveConfig = (values: any) => {
    if (!activeIntegration) return;

    const updated = integrations.map((item) => {
      if (item.id === activeIntegration.id) {
        return {
          ...item,
          connected: !!values.apiKey,
          apiKey: values.apiKey ? "••••••••••••••••••••••••" + values.apiKey.slice(-4) : "",
          webhookUrl: values.webhookUrl || "",
        };
      }
      return item;
    });

    setIntegrations(updated);
    setIsModalOpen(false);
    setActiveIntegration(null);
  };

  return (
    <div style={{ padding: "4px" }}>
      <div style={{ marginBottom: "20px" }}>
        <Title level={2} style={{ margin: 0 }}>Integrations</Title>
        <Text type="secondary">Connect external Telephony, Speech-to-Text (STT), Text-to-Speech (TTS), and Large Language Model (LLM) voice providers.</Text>
      </div>

      <Row gutter={[16, 16]}>
        {integrations.map((item) => (
          <Col xs={24} sm={12} key={item.id}>
            <Card
              hoverable
              actions={[
                item.connected ? (
                  <Button type="link" icon={<SettingOutlined />} onClick={() => handleOpenConfig(item)}>
                    Configure
                  </Button>
                ) : (
                  <Button type="link" icon={<PlusOutlined />} onClick={() => handleOpenConfig(item)}>
                    Connect
                  </Button>
                ),
              ]}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <Space align="start">
                  <div style={{ width: "40px", height: "40px", background: "rgba(24, 144, 255, 0.05)", borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <ApiOutlined style={{ fontSize: "20px", color: "#1890ff" }} />
                  </div>
                  <div>
                    <Title level={4} style={{ margin: 0 }}>{item.name}</Title>
                    <Paragraph type="secondary" style={{ margin: "4px 0 0 0", fontSize: "12px" }}>
                      Voice SDK and API pipeline provider configuration.
                    </Paragraph>
                  </div>
                </Space>
                <Tag color={item.connected ? "success" : "default"}>
                  {item.connected ? "✓ Connected" : "Not Connected"}
                </Tag>
              </div>

              {item.connected && (
                <div style={{ marginTop: "16px", background: "rgba(0,0,0,0.02)", padding: "10px", borderRadius: "4px" }}>
                  <Text type="secondary" style={{ fontSize: "11px", display: "block" }}>Masked API Credentials</Text>
                  <Text code style={{ fontSize: "12px" }}>{item.apiKey}</Text>
                  {item.webhookUrl && (
                    <div style={{ marginTop: "6px" }}>
                      <Text type="secondary" style={{ fontSize: "11px", display: "block" }}>Active Webhook Endpoint</Text>
                      <Text code style={{ fontSize: "12px" }}>{item.webhookUrl}</Text>
                    </div>
                  )}
                </div>
              )}
            </Card>
          </Col>
        ))}
      </Row>

      {/* Integration Setup Modal */}
      <Modal
        title={`Configure ${activeIntegration?.name}`}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          setActiveIntegration(null);
        }}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSaveConfig}>
          <Form.Item
            name="apiKey"
            label="API Auth Key / Secret"
            rules={[{ required: true, message: "API key is required" }]}
          >
            <Input.Password placeholder="Enter provider API credentials" />
          </Form.Item>

          {activeIntegration?.id === "vapi" && (
            <Form.Item
              name="webhookUrl"
              label="Callback Webhook URL"
              rules={[{ type: "url", message: "Must be a valid URL" }]}
            >
              <Input placeholder="https://api.yourdomain.com/vapi-webhook" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
};
