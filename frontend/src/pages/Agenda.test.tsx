import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ProvedorAvisos } from "../components/ui";
import type { Aula } from "../lib/types";
import { mockApi } from "../test/mockApi";
import Agenda from "./Agenda";

// "Hoje" = quinta 19/11/2026, 12:00 em São Paulo.
beforeEach(() => { vi.useFakeTimers({ toFake: ["Date"] }); vi.setSystemTime(new Date("2026-11-19T15:00:00Z")); });
afterEach(() => vi.useRealTimers());

const aula = (over: Partial<Aula>): Aula => ({
  id: "a1", titulo: "Pilates", tipo: "grupo", inicio: "2026-11-20T10:00:00Z", duracao_minutos: 50, capacidade: 4, ocupadas: 1, vagas: 3,
  participantes: [{ agendamento_id: "g1", aluno_id: "al1", aluno_nome: "Maria Souza", tipo: "regular", status: "agendado" }], ...over,
});
const tela = () => render(<ProvedorAvisos><Agenda /></ProvedorAvisos>);

describe("Agenda", () => {
  it("busca a semana (seg 00:00 → seg seguinte, no fuso do estúdio) e mostra a aula no dia/hora certos", async () => {
    const m = mockApi({ "GET /agenda/aulas": { body: [aula({})] } });
    tela();
    const coluna = (await screen.findByText("Sex 20/11")).parentElement!;
    expect(within(coluna).getByText("07:00")).toBeInTheDocument(); // 10:00 UTC = 07:00 SP
    expect(within(coluna).getByText("1/4")).toBeInTheDocument();
    expect(within(coluna).getByText("Maria")).toBeInTheDocument();
    const q = m.de("GET", "/agenda/aulas")[0].query;
    expect(q.get("de")).toBe("2026-11-16T03:00:00.000Z");
    expect(q.get("ate")).toBe("2026-11-23T03:00:00.000Z");
  });

  it("estado vazio convida a criar aulas", async () => {
    mockApi({ "GET /agenda/aulas": { body: [] } });
    tela();
    expect(await screen.findByText("Nenhuma aula nesta semana")).toBeInTheDocument();
  });

  it("cria grade recorrente enviando dias 0=segunda e hora local", async () => {
    const m = mockApi({ "GET /agenda/aulas": { body: [] }, "POST /agenda/aulas/recorrentes": { status: 201, body: [aula({}), aula({ id: "a2" })] } });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    tela();
    await user.click(await screen.findByRole("button", { name: "Nova aula" }));
    await user.click(screen.getByRole("tab", { name: "Grade recorrente" }));
    await user.click(screen.getByRole("button", { name: "Seg" }));
    await user.click(screen.getByRole("button", { name: "Qua" }));
    await user.click(screen.getByRole("button", { name: /Gerar grade/ }));
    expect(await screen.findByText("2 aulas criadas!")).toBeInTheDocument();
    expect(m.de("POST", "/agenda/aulas/recorrentes")[0].body).toMatchObject({ dias_semana: [0, 2], hora: "07:00", semanas: 4, data_inicio: "2026-11-19" });
  });

  it("cancelar mostra a mensagem do servidor (crédito gerado)", async () => {
    const m = mockApi({
      "GET /agenda/aulas": { body: [aula({})] },
      "GET /agenda/aulas/a1": { body: aula({}) },
      "GET /alunos": { body: [] },
      "POST /agenda/agendamentos/g1/cancelar": { body: { credito_gerado: true, mensagem: "Cancelado com 3h ou mais de antecedência: +1 crédito" } },
    });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    tela();
    await user.click(await screen.findByText("Pilates"));
    await user.click(await screen.findByRole("button", { name: "Cancelar" }));
    await user.click(screen.getByRole("button", { name: "Cancelar agendamento" }));
    expect(await screen.findByText(/\+1 crédito/)).toBeInTheDocument();
    expect(m.de("POST", "/agenda/agendamentos/g1/cancelar")).toHaveLength(1);
  });

  it("turma lotada aparece em destaque e o 409 do servidor vira aviso", async () => {
    const cheia = aula({ ocupadas: 4, vagas: 0 });
    mockApi({
      "GET /agenda/aulas": { body: [cheia] },
      "GET /agenda/aulas/a1": { body: cheia },
      "GET /alunos": { body: [{ id: "al9", nome: "Bruno", telefone: "11999999999", email: null, observacoes: null, ativo: true, creditos_reposicao: 0, creditos_validade_ate: null, criado_em: "" }] },
      "POST /agenda/aulas/a1/agendamentos": { status: 409, body: { detail: "Turma lotada: não há vagas neste horário." } },
    });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    tela();
    expect(await screen.findByText("4/4")).toHaveClass("bg-red-500");
    await user.click(screen.getByText("Pilates"));
    await user.selectOptions(await screen.findByRole("combobox"), "al9");
    await user.click(screen.getByRole("button", { name: /Tentar agendar/ }));
    expect(await screen.findByText("Turma lotada: não há vagas neste horário.")).toBeInTheDocument();
  });

  it("atendimento individual: envia tipo + paciente, nunca capacidade", async () => {
    const PAC = { id: "al7", nome: "Juliana Prado", telefone: "11999999999", email: null, observacoes: null, ativo: true, creditos_reposicao: 0, creditos_validade_ate: null, criado_em: "" };
    const m = mockApi({
      "GET /agenda/aulas": { body: [] },
      "GET /alunos": { body: [PAC] },
      "POST /agenda/aulas": { status: 201, body: aula({ tipo: "individual", capacidade: 1, ocupadas: 1, vagas: 0 }) },
    });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    tela();
    await user.click(await screen.findByRole("button", { name: "Nova aula" }));
    await user.click(screen.getByRole("radio", { name: /Individual/ }));
    expect(screen.getByLabelText("Título")).toHaveValue("Atendimento individual");
    await user.selectOptions(await screen.findByLabelText("Paciente (opcional)"), "al7");
    await user.clear(screen.getByLabelText("Hora"));
    await user.type(screen.getByLabelText("Hora"), "10:00");
    await user.click(screen.getByRole("button", { name: "Criar aula" }));
    expect(await screen.findByText("Aula criada!")).toBeInTheDocument();

    const body = m.de("POST", "/agenda/aulas")[0].body;
    expect(body).toMatchObject({ tipo: "individual", aluno_id: "al7", titulo: "Atendimento individual", inicio: "2026-11-19T13:00:00.000Z" });
    expect(body).not.toHaveProperty("capacidade");
  });

  it("card mostra o selo Individual", async () => {
    mockApi({ "GET /agenda/aulas": { body: [aula({ tipo: "individual", titulo: "Fisio", capacidade: 1, ocupadas: 1, vagas: 0 })] } });
    tela();
    expect(await screen.findByText("Individual")).toBeInTheDocument();
    expect(screen.getByText("1/1")).toBeInTheDocument();
  });
});
