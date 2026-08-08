import { createRequire } from "node:module";
import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const iranCity = require("iran-city");
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const cities = [...new Set(iranCity.allCities().map((item) => item.name.trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "fa"));
const provinces = [...new Set(iranCity.allProvinces().map((item) => item.name.trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "fa"));
const source = `export const IRAN_CITIES = ${JSON.stringify(cities, null, 2)} as const;\n\nexport const IRAN_PROVINCES = ${JSON.stringify(provinces, null, 2)} as const;\n`;
writeFileSync(resolve(root, "src/lib/iran-city-data.ts"), source, "utf8");
console.log(`Generated ${cities.length} cities and ${provinces.length} provinces`);
