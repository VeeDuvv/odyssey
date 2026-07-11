"use client";

import { EnterpriseProvider } from "@/lib/enterprise-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return <EnterpriseProvider>{children}</EnterpriseProvider>;
}
