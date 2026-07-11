"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { getEnterprise } from "./api";

interface EnterpriseContextType {
  enterpriseId: string | null;
  enterpriseName: string | null;
  isLoading: boolean;
  setEnterprise: (id: string, name: string) => void;
  clearEnterprise: () => void;
}

const EnterpriseContext = createContext<EnterpriseContextType>({
  enterpriseId: null,
  enterpriseName: null,
  isLoading: true,
  setEnterprise: () => {},
  clearEnterprise: () => {},
});

const STORAGE_KEY = "odyssey_enterprise";

export function EnterpriseProvider({ children }: { children: ReactNode }) {
  const [enterpriseId, setEnterpriseId] = useState<string | null>(null);
  const [enterpriseName, setEnterpriseName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      setIsLoading(false);
      return;
    }
    try {
      const { id, name } = JSON.parse(stored);
      // Validate the enterprise still exists
      getEnterprise(id)
        .then((data) => {
          if (data && !("error" in data)) {
            setEnterpriseId(id);
            setEnterpriseName(name);
          } else {
            localStorage.removeItem(STORAGE_KEY);
          }
        })
        .catch(() => {
          // Backend unreachable — keep stored values, they'll validate on next load
          setEnterpriseId(id);
          setEnterpriseName(name);
        })
        .finally(() => setIsLoading(false));
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      setIsLoading(false);
    }
  }, []);

  const setEnterprise = useCallback((id: string, name: string) => {
    setEnterpriseId(id);
    setEnterpriseName(name);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ id, name }));
  }, []);

  const clearEnterprise = useCallback(() => {
    setEnterpriseId(null);
    setEnterpriseName(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return (
    <EnterpriseContext.Provider
      value={{ enterpriseId, enterpriseName, isLoading, setEnterprise, clearEnterprise }}
    >
      {children}
    </EnterpriseContext.Provider>
  );
}

export function useEnterprise() {
  return useContext(EnterpriseContext);
}
