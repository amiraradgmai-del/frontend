import { RolePanelGuard } from "@/components/role-panel-guard";

const roles = ["admin"] as const;

export default function SupportLayout({ children }: { children: React.ReactNode }) {
  return <RolePanelGuard roles={roles} fallback="/app/dashboard">{children}</RolePanelGuard>;
}
