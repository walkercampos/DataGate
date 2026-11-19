import { describe, expect, it, vi } from "vitest";
import { mockApi } from "../test/mockApi";
import { ApiError, api, sessao, setOnUnauthorized } from "./api";

const LOGIN = { access_token: "tok-123", token_type: "bearer", usuario: { id: "u1", nome: "Ana", email: "a@a.com", papel: "admin", tenant_id: "t1", estudio_nome: "Studio" } };

describe("cliente da API", () => {
  it("envia o token Bearer e usa o prefixo /api", async () => {
    sessao.salvar(LOGIN);
    const m = mockApi({ "GET /alunos": { body: [] } });
    await api("/alunos", { query: { busca: "", apenas_ativos: true } });
    expect(m.chamadas[0].headers.Authorization).toBe("Bearer tok-123");
    expect(m.chamadas[0].query.get("apenas_ativos")).toBe("true");
    expect(m.chamadas[0].query.has("busca")).toBe(false); // vazio não vai na URL
  });

  it("transforma erro de negócio (409) em mensagem amigável", async () => {
    mockApi({ "POST /agenda/aulas/:id/agendamentos": { status: 409, body: { detail: "Turma lotada: não há vagas neste horário." } } });
    await expect(api("/agenda/aulas/x/agendamentos", { method: "POST", body: {} })).rejects.toMatchObject({
      status: 409, message: "Turma lotada: não há vagas neste horário.",
    });
  });

  it("junta erros de validação (422) campo a campo", async () => {
    mockApi({ "POST /alunos": { status: 422, body: { detail: [{ loc: ["body", "telefone"], msg: "String should have at least 10 characters" }] } } });
    await expect(api("/alunos", { method: "POST", body: {} })).rejects.toThrow("telefone: String should have at least 10 characters");
  });

  it("guarda o trace_id de erros 500", async () => {
    mockApi({ "GET /estudio": { status: 500, body: { detail: "Erro interno.", trace_id: "abc-123" } } });
    const e = (await api("/estudio").catch((x) => x)) as ApiError;
    expect(e.traceId).toBe("abc-123");
  });

  it("401 com sessão aberta dispara o logout", async () => {
    sessao.salvar(LOGIN);
    const sair = vi.fn();
    setOnUnauthorized(sair);
    mockApi({ "GET /alunos": { status: 401, body: { detail: "Sessão inválida" } } });
    await expect(api("/alunos")).rejects.toThrow("Sessão inválida");
    expect(sair).toHaveBeenCalledOnce();
  });

  it("API fora do ar vira mensagem clara", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api("/health")).rejects.toThrow("Não foi possível falar com a API");
  });
});
