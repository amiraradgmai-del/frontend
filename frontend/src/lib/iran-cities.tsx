"use client";
import { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import * as IranCity from "iran-city";
type Item = { id: number; name: string };

export function IranLocationFields({ city, onCityChange }: { city: string; onCityChange: (value: string) => void }) {
  const provinces = useMemo(() => IranCity.allProvinces() as Item[], []);
  const initialProvince = useMemo(() => { if (!city) return ""; const found = (IranCity.allCities() as Array<Item & { province_id?: number }>).find((item) => item.name === city); return provinces.find((item) => item.id === found?.province_id)?.name || ""; }, [city, provinces]);
  const [province, setProvince] = useState(initialProvince);
  const selected = provinces.find((item) => item.name === province.trim());
  const cities = selected ? IranCity.citiesOfProvince(selected.id) as Item[] : [];
  return <div className="grid gap-3 sm:grid-cols-2"><div><p className="mb-1 text-xs text-slate-500">استان</p><Input list="consultant-provinces" value={province} onChange={(event) => { setProvince(event.target.value); onCityChange(""); }} placeholder="تایپ یا انتخاب استان" autoComplete="off" /><datalist id="consultant-provinces">{provinces.map((item) => <option key={item.id} value={item.name} />)}</datalist></div><div><p className="mb-1 text-xs text-slate-500">شهر</p><Input list="consultant-cities" value={city} onChange={(event) => onCityChange(event.target.value)} placeholder={selected ? "تایپ یا انتخاب شهر" : "ابتدا استان را انتخاب کنید"} disabled={!selected} autoComplete="off" /><datalist id="consultant-cities">{cities.map((item) => <option key={item.id} value={item.name} />)}</datalist></div></div>;
}

export function IranCitySelect({ value, onChange }: { value: string; onChange: (value: string) => void }) { return <IranLocationFields city={value} onCityChange={onChange} />; }
