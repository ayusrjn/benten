import { AuthPage } from "@refinedev/antd";
import { Logo } from "../../components";

export const Login = () => {
  return (
    <AuthPage
      type="login"
      title={<Logo size={48} rounded />}
      formProps={{
        initialValues: { email: "admin@benten.ai", password: "password" },
      }}
    />
  );
};
