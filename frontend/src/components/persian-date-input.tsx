"use client";
import { useEffect, useState } from "react";

const monthNames = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];
const div = (a: number, b: number) => Math.trunc(a / b);
function toJalali(gy: number, gm: number, gd: number) { const dm=[0,31,59,90,120,151,181,212,243,273,304,334];let jy;if(gy>1600){jy=979;gy-=1600;}else{jy=0;gy-=621;}const gy2=gm>2?gy+1:gy;let d=365*gy+div(gy2+3,4)-div(gy2+99,100)+div(gy2+399,400)-80+gd+dm[gm-1];jy+=33*div(d,12053);d%=12053;jy+=4*div(d,1461);d%=1461;if(d>365){jy+=div(d-1,365);d=(d-1)%365;}return [jy,d<186?1+div(d,31):7+div(d-186,30),1+(d<186?d%31:(d-186)%30)]; }
function toGregorian(jy:number,jm:number,jd:number){jy+=1595;let d=-355668+365*jy+div(jy,33)*8+div(jy%33+3,4)+jd+(jm<7?(jm-1)*31:(jm-7)*30+186);let gy=400*div(d,146097);d%=146097;if(d>36524){gy+=100*div(--d,36524);d%=36524;if(d>=365)d++;}gy+=4*div(d,1461);d%=1461;if(d>365){gy+=div(d-1,365);d=(d-1)%365;}let gd=d+1;const leap=gy%4===0&&gy%100!==0||gy%400===0,s=[0,31,leap?29:28,31,30,31,30,31,31,30,31,30,31];let gm=1;while(gm<=12&&gd>s[gm])gd-=s[gm++];return[gy,gm,gd];}

export function PersianDateInput({value,onChange,required=false,includeTime=false}:{value:string;onChange:(value:string)=>void;required?:boolean;includeTime?:boolean}){
  const read=()=>{const date=value?new Date(value):null;return date&&!Number.isNaN(date.getTime())?toJalali(date.getFullYear(),date.getMonth()+1,date.getDate()):[0,0,0];};
  const [parts,setParts]=useState<number[]>(read); const [time,setTime]=useState(value.includes("T")?value.slice(11,16):"09:00");
  useEffect(()=>{if(value)setParts(read());},[value]);
  const change=(index:number,raw:string)=>{const next=[...parts];next[index]=Number(raw);setParts(next);if(!next.every(Boolean)){onChange("");return;}const [gy,gm,gd]=toGregorian(next[0],next[1],next[2]);const date=`${gy}-${String(gm).padStart(2,"0")}-${String(gd).padStart(2,"0")}`;onChange(includeTime?`${date}T${time}`:date);};
  const setClock=(clock:string)=>{setTime(clock);if(value)onChange(`${value.slice(0,10)}T${clock}`);};
  const years=Array.from({length:101},(_,i)=>1450-i),days=Array.from({length:parts[1]===12?30:parts[1]>6?30:31},(_,i)=>i+1);
  const cls="h-10 min-w-0 rounded-lg border bg-white px-2 text-sm";
  return <div className="grid grid-cols-[1fr_1.5fr_1fr] gap-2" dir="rtl"><select required={required} aria-label="سال شمسی" value={parts[0]||""} onChange={e=>change(0,e.target.value)} className={cls}><option value="">سال</option>{years.map(y=><option key={y}>{y}</option>)}</select><select required={required} aria-label="ماه شمسی" value={parts[1]||""} onChange={e=>change(1,e.target.value)} className={cls}><option value="">ماه</option>{monthNames.map((m,i)=><option key={m} value={i+1}>{m}</option>)}</select><select required={required} aria-label="روز شمسی" value={parts[2]||""} onChange={e=>change(2,e.target.value)} className={cls}><option value="">روز</option>{days.map(d=><option key={d}>{d}</option>)}</select>{includeTime&&<input aria-label="ساعت" type="time" value={time} onChange={e=>setClock(e.target.value)} className={`${cls} col-span-3`} />}</div>;
}
