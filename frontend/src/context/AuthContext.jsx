
import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import { API_BASE_URL } from "../api/client";

const AuthContext = createContext(null);

const ACCESS_TOKEN_KEY = "sharemeal_access_token";
const REFRESH_TOKEN_KEY = "sharemeal_refresh_token";

// Read saved tokens for the current browser session
const getAccessToken = () =>
  sessionStorage.getItem(ACCESS_TOKEN_KEY);

const getRefreshToken = () =>
  sessionStorage.getItem(REFRESH_TOKEN_KEY);

const saveTokens = (accessToken, refreshToken) => {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
};

const clearTokens = () => {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
};

// Common API response handler
async function handleResponse(response) {
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.error?.message ||
      data.detail ||
      data.message ||
      "Something went wrong"
    );
  }

  return data;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Send email OTP
  const sendOTP = async (email) => {
    const response = await fetch(
      `${API_BASE_URL}/auth/send-otp`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      }
    );

    return handleResponse(response);
  };

  // Verify OTP and log in
  const verifyOTP = async ({
    email,
    token,
    full_name,
    role,
    organization_name,
  }) => {
    const response = await fetch(
      `${API_BASE_URL}/auth/verify-otp`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          token,
          full_name,
          role,
          organization_name,
        }),
      }
    );

    const data = await handleResponse(response);

    if (!data.session?.access_token ||
        !data.session?.refresh_token) {
      throw new Error("Authentication tokens were not returned");
    }

    saveTokens(
      data.session.access_token,
      data.session.refresh_token
    );

    setUser(data.user || null);
    setProfile(data.profile || null);

    return data;
  };

  // Refresh expired access token
  const refreshAccessToken = async () => {
    const refreshToken = getRefreshToken();

    if (!refreshToken) {
      clearTokens();
      return null;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/auth/refresh`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            refresh_token: refreshToken,
          }),
        }
      );

      const data = await handleResponse(response);

      if (!data.access_token || !data.refresh_token) {
        throw new Error("Invalid refresh response");
      }

      saveTokens(data.access_token, data.refresh_token);

      return data.access_token;
    } catch (error) {
      clearTokens();
      setUser(null);
      setProfile(null);
      return null;
    }
  };

  // Get currently authenticated user
  const fetchCurrentUser = async (accessToken) => {
    const response = await fetch(
      `${API_BASE_URL}/auth/me`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );

    return handleResponse(response);
  };

  // Restore login when the page reloads
  useEffect(() => {
    const restoreSession = async () => {
      try {
        let accessToken = getAccessToken();

        if (!accessToken) {
          accessToken = await refreshAccessToken();
        }

        if (!accessToken) return;

        try {
          const data = await fetchCurrentUser(accessToken);
          setUser(data.user || data);
          setProfile(data.profile || data);
        } catch {
          accessToken = await refreshAccessToken();

          if (!accessToken) return;

          const data = await fetchCurrentUser(accessToken);
          setUser(data.user || data);
          setProfile(data.profile || data);
        }
      } catch {
        clearTokens();
        setUser(null);
        setProfile(null);
      } finally {
        setIsLoading(false);
      }
    };

    restoreSession();
  }, []);

  // Log out
  const logout = () => {
    clearTokens();
    setUser(null);
    setProfile(null);
  };

  // Authenticated API request
  const authFetch = async (endpoint, options = {}) => {
    let accessToken = getAccessToken();

    if (!accessToken) {
      accessToken = await refreshAccessToken();
    }

    if (!accessToken) {
      throw new Error("Please log in again");
    }

    const makeRequest = (token) =>
      fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
          ...options.headers,
          Authorization: `Bearer ${token}`,
        },
      });

    let response = await makeRequest(accessToken);

    if (response.status === 401) {
      accessToken = await refreshAccessToken();

      if (!accessToken) {
        throw new Error("Session expired. Please log in again.");
      }

      response = await makeRequest(accessToken);
    }

    return handleResponse(response);
  };

  const value = {
    user,
    profile,
    isLoading,
    isAuthenticated: Boolean(user),
    sendOTP,
    verifyOTP,
    logout,
    authFetch,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook for accessing authentication
export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider"
    );
  }

  return context;
}
