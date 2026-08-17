declare module "iran-city" {
  export type IranLocation = {
    id: number;
    name: string;
    province_id?: number;
    slug?: string;
  };

  export function allProvinces(): IranLocation[];
  export function allCities(): IranLocation[];
  export function citiesOfProvince(provinceId: number): IranLocation[];
  export function cityByName(name: string): IranLocation | undefined;
}
