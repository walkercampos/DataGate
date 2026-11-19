import type { AuthResp } from "./types";

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, "") || "/api";
const TOKEN_KEY = "sp_token";
const USER_KEY = "sp_usuario";

export class ApiError extends Error {
  constructor(message: string, public status: number, public traceId?: string) {
    super(message);
  }
}

let onUnauthorized: () => void = () => {};
export const setOnUnauthorized = (fn: () => void) => { onUnauthorized = fn; };

export const sessao = {
  token: () => localStorage.getItem(TOKEN_KEY),
  usuario: (): AuthResp["usuario"] | null => {
    try { return JSON.parse(localStorage.getItem(USER_KEY) ?? "null"); } catch { return null; }
  },
  salvar: (r: AuthResp) => {
    localStorage.setItem(TOKEN_KEY, r.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(r.usuario));
  },
  limpar: () => { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); },
};

function mensagemDeErro(body: unknown, status: number): { msg: string; trace?: string } {
  const b = body as { detail?: unknown; trace_id?: string } | null;
  const d = b?.detail;
  if (typeof d === "string") return { msg: d, trace: b?.trace_id };
  if (Array.isArray(d)) {
    const msgs = d.map((e: { loc?: unknown[]; msg?: string }) => {
      const campo = (e.loc ?? []).filter((x) => x !== "body" && x !== "query").join(".");
      const texto = (e.msg ?? "inválido").replace(/^Value error, /, "");
      return campo ? `${campo}: ${texto}` : texto;
    });
    return { msg: msgs.join(" · ") };
  }
  if (status === 0) return { msg: "Não foi possível falar com a API. Ela está rodando?" };
  return { msg: `Erro ${status}` };
}

export async function api<T = unknown>(path: string, opts: { method?: string; body?: unknown; query?: Record<string, unknown> } = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  const token = sessao.token();
  if (token) headers.Authorization = `Bearer ${token}`;

  let url = BASE + path;
  if (opts.query) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(opts.query)) if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    const s = qs.toString();
    if (s) url += "?" + s;
  }

  let res: Response;
  try {
    res = await fetch(url, { method: opts.method ?? "GET", headers, body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined });
  } catch {
    throw new ApiError(mensagemDeErro(null, 0).msg, 0);
  }
  if (res.status === 204) return undefined as T;
  const texto = await res.text();
  let body: unknown = null;
  try { body = texto ? JSON.parse(texto) : null; } catch { body = null; }
  if (!res.ok) {
    const { msg, trace } = mensagemDeErro(body, res.status);
    if (res.status === 401 && token) onUnauthorized();
    throw new ApiError(msg, res.status, trace);
  }
  return body as T;
}
