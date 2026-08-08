import { RolePanelGuard } from "@/components/role-panel-guard";

const roles = ["company_expert", "tax_expert"] as const;

export default function ConsultantLayout({ children }: { children: React.ReactNode }) {
  return <RolePanelGuard roles={roles} fallback="/app/dashboard">{children}</RolePanelGuard>;
}
