export const DIAS_CURTOS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
export const DIAS_LONGOS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

/** 0 = segunda ... 6 = domingo (mesma convenção da API). */
export const diaSemana = (d: Date) => (d.getDay() + 6) % 7;

export function inicioDaSemana(d: Date): Date {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  x.setDate(x.getDate() - diaSemana(x));
  return x;
}
export const somarDias = (d: Date, n: number) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
export const mesmoDia = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

const pad = (n: number) => String(n).padStart(2, "0");

/* Todas as datas/horas são exibidas e digitadas no FUSO DO ESTÚDIO (não no do navegador). */
let FUSO = Intl.DateTimeFormat().resolvedOptions().timeZone;
export const setFuso = (tz: string) => { FUSO = tz; };
export const getFuso = () => FUSO;

function partes(ts: number) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat("en-US", { timeZone: FUSO, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" })
      .formatToParts(new Date(ts)).map((x) => [x.type, x.value]),
  );
  return { ano: +p.year, mes: +p.month, dia: +p.day, hora: +p.hour, min: +p.minute, seg: +p.second };
}
const deslocamento = (ts: number) => {
  const q = partes(ts);
  return Date.UTC(q.ano, q.mes - 1, q.dia, q.hora, q.min, q.seg) - Math.floor(ts / 1000) * 1000;
};
/** Chave yyyy-mm-dd do instante ISO no fuso do estúdio. */
export const chaveDia = (iso: string) => { const q = partes(new Date(iso).getTime()); return `${q.ano}-${pad(q.mes)}-${pad(q.dia)}`; };
/** yyyy-mm-dd no fuso local */
export const isoData = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
/** data (yyyy-mm-dd) + hora (HH:mm) no fuso do estúdio -> ISO (UTC) */
export function isoDataHora(data: string, hora: string): string {
  const [a, m, d] = data.split("-").map(Number);
  const [h, mi] = hora.split(":").map(Number);
  const relogio = Date.UTC(a, m - 1, d, h, mi);
  let ts = relogio - deslocamento(relogio);
  const ajuste = deslocamento(ts);
  if (relogio - ajuste !== ts) ts = relogio - ajuste; // virada de horário de verão
  return new Date(ts).toISOString();
}

const f = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("pt-BR", { timeZone: FUSO, ...o });
export const fmtHora = (iso: string) => f({ hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
export const fmtData = (iso: string) => f({ day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(iso));
export const fmtDataHora = (iso: string) => f({ day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
export const fmtDiaMes = (d: Date) => new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(d).replace(".", "");
export const fmtDiaLongo = (iso: string) => {
  const t = f({ weekday: "long", day: "2-digit", month: "long" }).format(new Date(iso));
  return t.charAt(0).toUpperCase() + t.slice(1);
};
/** "2026-12-01" (data pura da API) -> 01/12/2026 sem deslocamento de fuso */
export const fmtDataPura = (s: string) => s.split("-").reverse().join("/");
export const fmtMoeda = (v: string | number) => Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
