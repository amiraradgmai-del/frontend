import type { Metadata } from "next";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";
import type { ConsultantProfile } from "@/lib/types";
import { AdvisorDirectory } from "./advisor-directory";

export const metadata: Metadata = {
  title: "فهرست مشاوران مالیاتی",
  description: "جست‌وجو و مشاهده مشاوران مالیاتی تأییدشده بر اساس شهر، تخصص و امتیاز.",
};

async function advisors(): Promise<ConsultantProfile[]> {
  try {
    const response = await fetch(`${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/v1/consultations/public/advisors?limit=24`, { next: { revalidate: 120 } });
    return response.ok ? response.json() : [];
  } catch {
    return [];
  }
}

export default async function AdvisorsPage() {
  const items = await advisors();
  return <main><PublicHeader /><AdvisorDirectory items={items} /><PublicFooter /></main>;
}
