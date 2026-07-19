import { AuthPage } from "@refinedev/antd";
import { Logo } from "../../components";

export const ForgotPassword = () => {
  return <AuthPage type="forgotPassword" title={<Logo size={48} rounded />} />;
};
