import {
  Refine,
  Authenticated,
  WelcomePage,
} from "@refinedev/core";
import { DevtoolsPanel, DevtoolsProvider } from "@refinedev/devtools";
import { RefineKbar, RefineKbarProvider } from "@refinedev/kbar";

import {
  ErrorComponent,
  useNotificationProvider,
  ThemedLayout,
  ThemedSider,
} from "@refinedev/antd";
import "@refinedev/antd/dist/reset.css";
import "./sidebar.css";


import { App as AntdApp } from "antd";
import { BrowserRouter, Route, Routes, Outlet } from "react-router";
import routerProvider, {
  NavigateToResource,
  CatchAllNavigate,
  UnsavedChangesNotifier,
  DocumentTitleHandler,
} from "@refinedev/react-router";
import { dataProvider } from "./providers/data";
import { ColorModeContextProvider } from "./contexts/color-mode";
import { Header } from "./components/header";
import { Logo } from "./components";
import { Login } from "./pages/login";
import { Register } from "./pages/register";
import { ForgotPassword } from "./pages/forgotPassword";
import { Dashboard } from "./pages/dashboard";
import { IntegrationsPage } from "./pages/integrations";
import { AgentsPage } from "./pages/agents";
import { authProvider } from "./providers/auth";

import {
  DashboardOutlined,
  MessageOutlined,
  RobotOutlined,
  AlertOutlined,
  ApiOutlined,
} from "@ant-design/icons";

function App() {
  return (
    <BrowserRouter>
      <RefineKbarProvider>
        <ColorModeContextProvider>
          <AntdApp>
            <DevtoolsProvider>
              <Refine
                dataProvider={dataProvider}
                notificationProvider={useNotificationProvider}
                routerProvider={routerProvider}
                authProvider={authProvider}
                resources={[
                  {
                    name: "dashboard",
                    list: "/dashboard",
                    meta: {
                      label: "Dashboard",
                      icon: <DashboardOutlined />,
                    },
                  },
                  {
                    name: "conversations",
                    list: "/conversations",
                    show: "/conversations/:id",
                    meta: {
                      label: "Conversations",
                      icon: <MessageOutlined />,
                    },
                  },
                  {
                    name: "agents",
                    list: "/agents",
                    meta: {
                      label: "Agents",
                      icon: <RobotOutlined />,
                    },
                  },
                  {
                    name: "alerts",
                    list: "/alerts",
                    meta: {
                      label: "Alerts",
                      icon: <AlertOutlined />,
                    },
                  },
                  {
                    name: "integrations",
                    list: "/integrations",
                    meta: {
                      label: "Integrations",
                      icon: <ApiOutlined />,
                    },
                  },
                ]}
                options={{
                  syncWithLocation: true,
                  warnWhenUnsavedChanges: true,
                  projectId: "R0DyBJ-E08YTs-V5d191",
                  title: {
                    text: "Benten",
                    icon: <img src="/icon.png" width={24} style={{ borderRadius: "6px" }} />,
                  },
                }}
              >
                <Routes>
                  <Route
                    element={
                      <Authenticated
                        key="authenticated-inner"
                        fallback={<CatchAllNavigate to="/login" />}
                      >
                        <ThemedLayout
                          Header={Header}
                          Sider={(props) => (
                            <ThemedSider
                              {...props}
                              Title={({ collapsed }) => (
                                <Logo collapsed={collapsed} />
                              )}
                            />
                          )}
                        >
                          <Outlet />
                        </ThemedLayout>
                      </Authenticated>
                    }
                  >
                    <Route
                      index
                      element={<NavigateToResource resource="dashboard" />}
                    />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/conversations" element={<div style={{ padding: "24px" }}>Conversations Placeholder</div>} />
                    <Route path="/conversations/:id" element={<div style={{ padding: "24px" }}>Conversation Detail Placeholder</div>} />
                    <Route path="/agents" element={<AgentsPage />} />
                    <Route path="/alerts" element={<div style={{ padding: "24px" }}>Alerts Placeholder</div>} />
                    <Route path="/integrations" element={<IntegrationsPage />} />
                  </Route>
                  <Route
                    element={
                      <Authenticated
                        key="authenticated-outer"
                        fallback={<Outlet />}
                      >
                        <NavigateToResource />
                      </Authenticated>
                    }
                  >
                    <Route path="/login" element={<Login />} />
                    <Route path="/register" element={<Register />} />
                    <Route path="/forgot-password" element={<ForgotPassword />} />
                  </Route>
                  <Route path="*" element={<ErrorComponent />} />
                </Routes>

                <RefineKbar />
                <UnsavedChangesNotifier />
                <DocumentTitleHandler
                  handler={({ resource }) => {
                    if (resource) {
                      return `${resource.meta?.label ?? resource.name} | Benten`;
                    }
                    return "Benten";
                  }}
                />
              </Refine>
              <DevtoolsPanel />
            </DevtoolsProvider>
          </AntdApp>
        </ColorModeContextProvider>
      </RefineKbarProvider>
    </BrowserRouter>
  );
}

export default App;
