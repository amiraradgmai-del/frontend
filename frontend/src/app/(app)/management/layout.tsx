import { RolePanelGuard } from "@/components/role-panel-guard";

const roles = ["system_admin"] as const;

export default function ManagementLayout({ children }: { children: React.ReactNode }) {
  return <RolePanelGuard roles={roles} fallback="/app/dashboard">{children}</RolePanelGuard>;
}
