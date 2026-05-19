import {
  Refine,
  GitHubBanner,
  WelcomePage,
  Authenticated,
} from "@refinedev/core";
import { DevtoolsPanel, DevtoolsProvider } from "@refinedev/devtools";
import { RefineKbar, RefineKbarProvider } from "@refinedev/kbar";

import {
  AuthPage,
  ErrorComponent,
  useNotificationProvider,
  ThemedLayout,
  ThemedSider,
} from "@refinedev/antd";
import "@refinedev/antd/dist/reset.css";

import { App as AntdApp } from "antd";
import { BrowserRouter, Route, Routes, Outlet } from "react-router";
import routerProvider, {
  NavigateToResource,
  CatchAllNavigate,
  UnsavedChangesNotifier,
  DocumentTitleHandler,
} from "@refinedev/react-router";

import {
  DashboardOutlined,
  ProjectOutlined,
  AudioOutlined,
  MessageOutlined,
  AlertOutlined,
  ApiOutlined,
  TeamOutlined,
  SettingOutlined,
} from "@ant-design/icons";

import { dataProvider } from "./providers/data";
import { ColorModeContextProvider } from "./contexts/color-mode";
import { Header } from "./components/header";
import { Login } from "./pages/login";
import { Register } from "./pages/register";
import { ForgotPassword } from "./pages/forgotPassword";
import { authProvider } from "./providers/auth";

import { Dashboard } from "./pages/dashboard";
import { ProjectList } from "./pages/projects/list";
import { AgentList } from "./pages/agents/list";
import { AgentShow } from "./pages/agents/show";
import { ConversationList } from "./pages/conversations/list";
import { ConversationShow } from "./pages/conversations/show";
import { AlertList } from "./pages/alerts/list";
import { IntegrationList } from "./pages/integrations/list";
import { OrganizationList } from "./pages/organization/list";
import { SettingsList } from "./pages/settings/list";

function App() {
  return (
    <BrowserRouter>
      <GitHubBanner />
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
                    list: "/",
                    meta: {
                      label: "Dashboard",
                      icon: <DashboardOutlined />,
                    },
                  },
                  {
                    name: "projects",
                    list: "/projects",
                    meta: {
                      label: "Projects",
                      icon: <ProjectOutlined />,
                    },
                  },
                  {
                    name: "agents",
                    list: "/agents",
                    show: "/agents/show/:id",
                    meta: {
                      label: "Agents",
                      icon: <AudioOutlined />,
                    },
                  },
                  {
                    name: "conversations",
                    list: "/conversations",
                    show: "/conversations/show/:id",
                    meta: {
                      label: "Conversations",
                      icon: <MessageOutlined />,
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
                  {
                    name: "organization",
                    list: "/organization",
                    meta: {
                      label: "Organization",
                      icon: <TeamOutlined />,
                    },
                  },
                  {
                    name: "settings",
                    list: "/settings",
                    meta: {
                      label: "Settings",
                      icon: <SettingOutlined />,
                    },
                  },
                ]}
                options={{
                  syncWithLocation: true,
                  warnWhenUnsavedChanges: true,
                  projectId: "mXN0hU-RELUA4-bKOkIq",
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
                          Sider={(props) => <ThemedSider {...props} fixed />}
                        >
                          <Outlet />
                        </ThemedLayout>
                      </Authenticated>
                    }
                  >
                    <Route
                      index
                      element={<Dashboard />}
                    />
                    <Route path="/projects">
                      <Route index element={<ProjectList />} />
                    </Route>
                    <Route path="/agents">
                      <Route index element={<AgentList />} />
                      <Route path="show/:id" element={<AgentShow />} />
                    </Route>
                    <Route path="/conversations">
                      <Route index element={<ConversationList />} />
                      <Route path="show/:id" element={<ConversationShow />} />
                    </Route>
                    <Route path="/alerts">
                      <Route index element={<AlertList />} />
                    </Route>
                    <Route path="/integrations">
                      <Route index element={<IntegrationList />} />
                    </Route>
                    <Route path="/organization">
                      <Route index element={<OrganizationList />} />
                    </Route>
                    <Route path="/settings">
                      <Route index element={<SettingsList />} />
                    </Route>
                    <Route path="*" element={<ErrorComponent />} />
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
                    <Route
                      path="/forgot-password"
                      element={<ForgotPassword />}
                    />
                  </Route>
                </Routes>

                <RefineKbar />
                <UnsavedChangesNotifier />
                <DocumentTitleHandler />
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

// Activity: simulated update on 2026-03-13

// Activity: simulated update on 2026-05-19
