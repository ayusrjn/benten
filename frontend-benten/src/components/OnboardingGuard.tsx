import React from "react";
import { useGetIdentity } from "@refinedev/core";
import { Spin } from "antd";
import { Navigate, Outlet, useLocation } from "react-router";

export const OnboardingGuard: React.FC = () => {
  const { data: identity, isLoading } = useGetIdentity<any>();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <Spin size="large" tip="Loading Benten settings..." />
      </div>
    );
  }

  // User has NOT completed onboarding
  if (identity && identity.onboardingCompleted === false) {
    if (location.pathname !== "/onboarding") {
      return <Navigate to="/onboarding" replace />;
    }
  } 
  // User HAS completed onboarding
  else if (identity && identity.onboardingCompleted === true) {
    if (location.pathname === "/onboarding") {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return <Outlet />;
};
