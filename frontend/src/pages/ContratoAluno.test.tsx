import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProvedorAvisos } from "../components/ui";
import type { Aluno } from "../lib/types";
import { mockApi } from "../test/mockApi";
import ContratoAluno from "./ContratoAluno";

const ALUNO: Aluno = { id: "al1", nome: "Maria", telefone: "11987654321", email: null, observacoes: null, ativo: true, creditos_reposicao: 0, creditos_validade_ate: null, criado_em: "" };
const PLANO = { id: "p2", nome: "2x por semana", aulas_por_semana: 2, valor_mensal: "350.00", ativo: true, criado_em: "" };

describe("Contrato do aluno", () => {
  it("contrata enviando só IDs, data e horários (preço vem do servidor)", async () => {
    const m = mockApi({
      "GET /contratos": { body: [] },
      "GET /planos": { body: [PLANO] },
      "POST /contratos": { status: 201, body: { contrato: {}, grade: { agendadas: 8, ja_existentes: 0, aulas_criadas: 8, lotadas: [] } } },
    });
    render(<ProvedorAvisos><ContratoAluno aluno={ALUNO} onMudou={vi.fn()} /></ProvedorAvisos>);
    await userEvent.click(await screen.findByRole("button", { name: /Contratar plano/ }));
    await userEvent.selectOptions(await screen.findByLabelText("Plano"), "p2");
    // O plano 2x exige exatamente 2 horários: a tela já oferece 2 linhas.
    expect(screen.getAllByDisplayValue("07:00")).toHaveLength(2);
    await userEvent.click(screen.getByRole("button", { name: "Contratar e gerar grade" }));

    const body = m.de("POST", "/contratos")[0].body;
    expect(Object.keys(body).sort()).toEqual(["aluno_id", "data_inicio", "horarios", "plano_id"]);
    expect(body.horarios).toEqual([{ dia_semana: 0, hora: "07:00" }, { dia_semana: 2, hora: "07:00" }]);
    expect(await screen.findByText(/8 aula\(s\) agendada\(s\)/)).toBeInTheDocument();
  });

  it("mostra o contrato ativo com horários e valor", async () => {
    mockApi({
      "GET /contratos": { body: [{ id: "c1", aluno_id: "al1", aluno_nome: "Maria", plano_id: "p2", plano_nome: "2x por semana", aulas_por_semana: 2, valor_mensal: "350.00", data_inicio: "2026-11-01", data_fim: null, status: "ativo", horarios: [{ dia_semana: 0, hora: "07:00:00" }, { dia_semana: 3, hora: "18:30:00" }], criado_em: "" }] },
    });
    render(<ProvedorAvisos><ContratoAluno aluno={ALUNO} onMudou={vi.fn()} /></ProvedorAvisos>);
    expect(await screen.findByText("Segunda · 07:00")).toBeInTheDocument();
    expect(screen.getByText("Quinta · 18:30")).toBeInTheDocument();
    expect(screen.getByText(/R\$\s350,00\/mês/)).toBeInTheDocument();
  });
});
