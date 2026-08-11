import React from "react";
import { useRegister } from "@refinedev/core";
import { Form, Input, Button, Card, Typography, Layout, theme, message } from "antd";
import { useNavigate } from "react-router";
import { Logo } from "../../components";

const { Title, Text, Link } = Typography;

export const Register: React.FC = () => {
  const { mutate: register, isLoading } = useRegister<any>() as any;
  const navigate = useNavigate();
  const { token } = theme.useToken();

  const onFinish = (values: any) => {
    register(
      {
        email: values.email,
        password: values.password,
        fullName: values.fullName,
        orgName: values.orgName,
      },
      {
        onSuccess: (data: any) => {
          if (data && data.success === false) {
            message.error(data.error?.message || "Registration failed");
          } else {
            message.success("Registered successfully!");
            navigate("/onboarding");
          }
        },
        onError: (error: any) => {
          message.error(error?.message || "Registration failed");
        }
      }
    );
  };

  return (
    <Layout style={{ minHeight: "100vh", display: "flex", justifyContent: "center", alignItems: "center", background: token.colorBgContainer }}>
      <div style={{ width: "100%", maxWidth: "450px", padding: "24px" }}>
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <Logo size={48} rounded />
        </div>
        <Card bordered={false} style={{ boxShadow: token.boxShadowSecondary, borderRadius: "12px" }}>
          <Title level={3} style={{ textAlign: "center", marginBottom: "24px", color: token.colorTextHeading }}>
            Create an Account
          </Title>
          <Form
            name="register"
            layout="vertical"
            requiredMark="optional"
            onFinish={onFinish}
            autoComplete="off"
            initialValues={{ fullName: "", orgName: "", email: "", password: "" }}
          >
            <Form.Item
              name="fullName"
              label="Full Name"
              rules={[{ required: true, message: "Please enter your full name" }]}
            >
              <Input placeholder="John Doe" size="large" />
            </Form.Item>

            <Form.Item
              name="orgName"
              label="Organization Name"
              rules={[{ required: true, message: "Please enter your organization name" }]}
            >
              <Input placeholder="Acme Corp" size="large" />
            </Form.Item>

            <Form.Item
              name="email"
              label="Work Email"
              rules={[
                { required: true, message: "Please enter your email address" },
                { type: "email", message: "Please enter a valid email address" },
              ]}
            >
              <Input placeholder="john@example.com" size="large" />
            </Form.Item>

            <Form.Item
              name="password"
              label="Password"
              rules={[{ required: true, message: "Please enter your password" }]}
            >
              <Input.Password placeholder="●●●●●●●●" size="large" />
            </Form.Item>

            <Form.Item style={{ marginBottom: "8px", marginTop: "16px" }}>
              <Button type="primary" htmlType="submit" size="large" block loading={isLoading}>
                Sign up
              </Button>
            </Form.Item>
          </Form>
          <div style={{ textAlign: "center", marginTop: "16px" }}>
            <Text style={{ fontSize: "14px" }}>
              Already registered? <Link onClick={() => navigate("/login")}>Sign in</Link>
            </Text>
          </div>
        </Card>
      </div>
    </Layout>
  );
};
