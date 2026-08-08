import { redirect } from "next/navigation";

export default function NewConsultantPage() {
  redirect("/management/consultants#add-consultant");
}
