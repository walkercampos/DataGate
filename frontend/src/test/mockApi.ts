import { vi } from "vitest";

type Resposta = { status?: number; body?: unknown } | ((req: Chamada) => { status?: number; body?: unknown });
export type Chamada = { metodo: string; caminho: string; query: URLSearchParams; body: any; headers: Record<string, string> };

/** Substitui o fetch global: rotas no formato "GET /alunos" (sem o prefixo /api). Registra todas as chamadas. */
export function mockApi(rotas: Record<string, Resposta>) {
  const chamadas: Chamada[] = [];
  const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
    const u = new URL(url, "http://teste");
    const caminho = u.pathname.replace(/^\/api/, "");
    const metodo = (init.method ?? "GET").toUpperCase();
    const req: Chamada = {
      metodo, caminho, query: u.searchParams,
      body: init.body ? JSON.parse(String(init.body)) : undefined,
      headers: (init.headers ?? {}) as Record<string, string>,
    };
    chamadas.push(req);
    const chave = Object.keys(rotas).find((k) => {
      const [m, p] = k.split(" ");
      const re = new RegExp("^" + p.replace(/:[a-z_]+/g, "[^/]+") + "$");
      return m === metodo && re.test(caminho);
    });
    if (!chave) return new Response(JSON.stringify({ detail: `rota não mockada: ${metodo} ${caminho}` }), { status: 404 });
    const r = typeof rotas[chave] === "function" ? (rotas[chave] as Function)(req) : rotas[chave];
    const status = r.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(r.body ?? null), { status, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { chamadas, de: (metodo: string, caminho: string) => chamadas.filter((c) => c.metodo === metodo && c.caminho === caminho) };
}
