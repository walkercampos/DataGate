import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProvedorAvisos } from "../components/ui";
import type { Aluno } from "../lib/types";
import { mockApi } from "../test/mockApi";
import Alunos, { mascaraTelefone } from "./Alunos";

const ALUNO: Aluno = { id: "al1", nome: "Maria Souza", telefone: "(11) 98765-4321", email: null, observacoes: null, ativo: true, creditos_reposicao: 2, creditos_validade_ate: "2026-12-19T12:00:00Z", criado_em: "2026-11-01T12:00:00Z" };

describe("Alunos", () => {
  it("máscara de telefone", () => {
    expect(mascaraTelefone("11987654321")).toBe("(11) 98765-4321");
    expect(mascaraTelefone("1132654321")).toBe("(11) 3265-4321");
    expect(mascaraTelefone("abc11")).toBe("(11");
  });

  it("lista alunos com selo de créditos de reposição", async () => {
    mockApi({ "GET /alunos": { body: [ALUNO] } });
    render(<ProvedorAvisos><Alunos abrir={vi.fn()} /></ProvedorAvisos>);
    expect(await screen.findByText("Maria Souza")).toBeInTheDocument();
    expect(screen.getByText(/2 reposições/)).toBeInTheDocument();
  });

  it("cadastro envia os dados SEM créditos (quem controla é o servidor)", async () => {
    const m = mockApi({ "GET /alunos": { body: [] }, "POST /alunos": { status: 201, body: { ...ALUNO, creditos_reposicao: 0 } } });
    const abrir = vi.fn();
    render(<ProvedorAvisos><Alunos abrir={abrir} /></ProvedorAvisos>);
    await userEvent.click(await screen.findByRole("button", { name: "Novo aluno" }));
    await userEvent.type(screen.getByLabelText("Nome completo"), "Maria Souza");
    await userEvent.type(screen.getByLabelText("Telefone (WhatsApp)"), "11987654321");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    const body = m.de("POST", "/alunos")[0].body;
    expect(body).toEqual({ nome: "Maria Souza", telefone: "(11) 98765-4321", email: null, observacoes: null });
    expect(body).not.toHaveProperty("creditos_reposicao");
    expect(abrir).toHaveBeenCalledWith("al1");
  });

  it("busca filtra pela API", async () => {
    const m = mockApi({ "GET /alunos": { body: [] } });
    render(<ProvedorAvisos><Alunos abrir={vi.fn()} /></ProvedorAvisos>);
    await userEvent.type(screen.getByPlaceholderText(/Buscar/), "mar");
    await vi.waitFor(() => expect(m.de("GET", "/alunos").some((c) => c.query.get("busca") === "mar")).toBe(true));
  });
});
