import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .get("/auth/me")
      .then((response) => {
        if (!active) return;
        setUser(response.data.user);
        setSession(response.data);
      })
      .catch(() => {
        if (!active) return;
        setUser(null);
        setSession(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null);
      setSession(null);
    };
    window.addEventListener("vigil:unauthorized", onUnauthorized);
    return () => window.removeEventListener("vigil:unauthorized", onUnauthorized);
  }, []);

  const value = useMemo(
    () => ({
      user,
      session,
      loading,
      async login(email, password) {
        await api.post("/auth/login", { email, password });
        const me = await api.get("/auth/me");
        setUser(me.data.user);
        setSession(me.data);
        return me.data.user;
      },
      async register(payload) {
        await api.post("/auth/register", payload);
        const me = await api.get("/auth/me");
        setUser(me.data.user);
        setSession(me.data);
        return me.data.user;
      },
      async logout() {
        await api.post("/auth/logout");
        setUser(null);
        setSession(null);
      },
      refresh(next) {
        setUser(next.user || next);
        if (next.session_expires_at) setSession(next);
      },
    }),
    [user, session, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
