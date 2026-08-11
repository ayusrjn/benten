import type { AuthProvider } from "@refinedev/core";
import { API_URL, TOKEN_KEY } from "./constants";

export const authProvider: AuthProvider = {
  login: async ({ email, username, password }) => {
    try {
      const loginEmail = email || username;
      if (!loginEmail || !password) {
        return {
          success: false,
          error: {
            name: "LoginError",
            message: "Email and password are required.",
          },
        };
      }

      // FastAPI login endpoint expects application/x-www-form-urlencoded
      const formData = new URLSearchParams();
      formData.append("username", loginEmail);
      formData.append("password", password);

      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData.toString(),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          success: false,
          error: {
            name: "LoginError",
            message: errorData.detail || "Invalid email or password",
          },
        };
      }

      const data = await response.json();
      localStorage.setItem(TOKEN_KEY, data.access_token);

      return {
        success: true,
        redirectTo: "/",
      };
    } catch (error: any) {
      return {
        success: false,
        error: {
          name: "LoginError",
          message: error.message || "An unexpected error occurred during login.",
        },
      };
    }
  },
  register: async ({ email, password, fullName, orgName }) => {
    try {
      if (!email || !password || !orgName) {
        return {
          success: false,
          error: {
            name: "RegisterError",
            message: "Email, password, and Organization Name are required.",
          },
        };
      }

      const response = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName || null,
          org_name: orgName,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          success: false,
          error: {
            name: "RegisterError",
            message: errorData.detail || "Registration failed.",
          },
        };
      }

      // Automatically login the user after successful registration
      return authProvider.login({ email, password });
    } catch (error: any) {
      return {
        success: false,
        error: {
          name: "RegisterError",
          message: error.message || "An unexpected error occurred during registration.",
        },
      };
    }
  },
  logout: async () => {
    localStorage.removeItem(TOKEN_KEY);
    return {
      success: true,
      redirectTo: "/login",
    };
  },
  check: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      return {
        authenticated: true,
      };
    }

    return {
      authenticated: false,
      redirectTo: "/login",
    };
  },
  getPermissions: async () => null,
  getIdentity: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      return null;
    }

    try {
      const response = await fetch(`${API_URL}/auth/me`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        // If identity check fails (e.g. token expired), trigger logout
        localStorage.removeItem(TOKEN_KEY);
        return null;
      }

      const data = await response.json();
      return {
        id: data.id,
        name: data.full_name || data.email,
        email: data.email,
        onboardingCompleted: data.onboarding_completed,
        avatar: `https://api.dicebear.com/7.x/adventurer/svg?seed=${encodeURIComponent(data.email)}`,
      };
    } catch (error) {
      console.error("Failed to fetch user identity:", error);
      return null;
    }
  },
  onError: async (error) => {
    console.error("Auth provider error:", error);
    if (error.status === 401 || error.statusCode === 401) {
      localStorage.removeItem(TOKEN_KEY);
      return {
        logout: true,
        redirectTo: "/login",
      };
    }
    return { error };
  },
};
