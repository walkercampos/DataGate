import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ProvedorAvisos } from "../components/ui";
import type { Aluno, Registro } from "../lib/types";
import { mockApi } from "../test/mockApi";
import ProntuarioAluno from "./ProntuarioAluno";

const ALUNO = { id: "al1", nome: "Maria" } as Aluno;
const base: Registro = {
  id: "r1", aluno_id: "al1", agendamento_id: null, tipo: "avaliacao", titulo: "Avaliação física inicial", conteudo: "Lombalgia.", dor_eva: 6,
  autor_id: "u1", autor_nome: "Ana", status: "rascunho", assinado_por: null, assinado_por_nome: null, assinado_em: null, hash_sha256: null,
  criado_em: "2026-11-19T12:00:00Z", atualizado_em: null,
};
const HASH = "a".repeat(64);
const assinado: Registro = { ...base, status: "assinado", assinado_por: "u1", assinado_por_nome: "Ana", assinado_em: "2026-11-19T13:00:00Z", hash_sha256: HASH };

describe("Prontuário", () => {
  it("rascunho pode ser editado, assinado e excluído", async () => {
    mockApi({ "GET /alunos/al1/prontuario": { body: [base] } });
    render(<ProvedorAvisos><ProntuarioAluno aluno={ALUNO} /></ProvedorAvisos>);
    expect(await screen.findByText("Rascunho")).toBeInTheDocument();
    for (const b of ["Editar", "Assinar", "Excluir"]) expect(screen.getByRole("button", { name: b })).toBeInTheDocument();
  });

  it("registro assinado é somente leitura e mostra o hash", async () => {
    mockApi({ "GET /alunos/al1/prontuario": { body: [assinado] } });
    render(<ProvedorAvisos><ProntuarioAluno aluno={ALUNO} /></ProvedorAvisos>);
    expect(await screen.findByText(`SHA-256: ${HASH}`)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Excluir" })).not.toBeInTheDocument();
  });

  it("assinar pede confirmação e chama a API", async () => {
    let assinou = false;
    const m = mockApi({
      "GET /alunos/al1/prontuario": () => ({ body: [assinou ? assinado : base] }),
      "POST /prontuario/r1/assinar": () => { assinou = true; return { body: assinado }; },
    });
    render(<ProvedorAvisos><ProntuarioAluno aluno={ALUNO} /></ProvedorAvisos>);
    await userEvent.click(await screen.findByRole("button", { name: "Assinar" }));
    expect(screen.getByText(/bloqueado para sempre/)).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Assinar" }).at(-1)!);
    expect(m.de("POST", "/prontuario/r1/assinar")).toHaveLength(1);
    expect(await screen.findByText(`SHA-256: ${HASH}`)).toBeInTheDocument();
  });

  it("verificação mostra alerta quando o conteúdo foi adulterado", async () => {
    mockApi({
      "GET /alunos/al1/prontuario": { body: [assinado] },
      "GET /prontuario/r1/verificar": { body: { id: "r1", hash_registrado: HASH, hash_recalculado: "b".repeat(64), integro: false } },
    });
    render(<ProvedorAvisos><ProntuarioAluno aluno={ALUNO} /></ProvedorAvisos>);
    await userEvent.click(await screen.findByRole("button", { name: /Verificar integridade/ }));
    expect(await screen.findByText("Adulterado!")).toBeInTheDocument();
  });

  it("novo registro envia tipo, título, texto e dor", async () => {
    const m = mockApi({ "GET /alunos/al1/prontuario": { body: [] }, "POST /alunos/al1/prontuario": { status: 201, body: base } });
    render(<ProvedorAvisos><ProntuarioAluno aluno={ALUNO} /></ProvedorAvisos>);
    await userEvent.click(await screen.findByRole("button", { name: /Novo registro/ }));
    await userEvent.type(screen.getByRole("textbox", { name: /^Avaliação/ }), "Lombalgia crônica.");
    await userEvent.click(screen.getByRole("button", { name: "6" }));
    await userEvent.click(screen.getByRole("button", { name: "Salvar rascunho" }));
    expect(m.de("POST", "/alunos/al1/prontuario")[0].body).toEqual({ tipo: "avaliacao", titulo: "Avaliação física inicial", conteudo: "Lombalgia crônica.", dor_eva: 6 });
  });
});
