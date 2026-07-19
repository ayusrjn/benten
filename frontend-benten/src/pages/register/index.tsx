import { AuthPage } from "@refinedev/antd";
import { Logo } from "../../components";

export const Register = () => {
  return <AuthPage type="register" title={<Logo size={48} rounded />} />;
};
