import { IRAN_CITIES, IRAN_PROVINCES } from "@/lib/iran-city-data";

export { IRAN_CITIES, IRAN_PROVINCES };

export type IranCity = (typeof IRAN_CITIES)[number];

export function IranCitySelect({
  value,
  onChange,
  required = false,
  id,
}: {
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  id?: string;
}) {
  return (
    <select id={id} value={value} required={required} onChange={(event) => onChange(event.target.value)} className="h-10 w-full rounded-lg border bg-white px-3 text-sm">
      <option value="">انتخاب شهر</option>
      {IRAN_CITIES.map((city) => <option key={city} value={city}>{city}</option>)}
    </select>
  );
}
