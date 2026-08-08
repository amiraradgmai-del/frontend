import { RolePanelGuard } from "@/components/role-panel-guard";

const roles = ["user"] as const;

export default function UserPanelLayout({ children }: { children: React.ReactNode }) {
  return <RolePanelGuard roles={roles} fallback="/management">{children}</RolePanelGuard>;
}
