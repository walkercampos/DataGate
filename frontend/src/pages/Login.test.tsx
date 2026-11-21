import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProvedorAvisos } from "../components/ui";
import { sessao } from "../lib/api";
import { mockApi } from "../test/mockApi";
import Login from "./Login";

const USUARIO = { id: "u1", nome: "Ana", email: "ana@studio.com", papel: "admin", tenant_id: "t1", estudio_nome: "Studio Equilíbrio" };
const tela = (onEntrar = vi.fn()) => render(<ProvedorAvisos><Login onEntrar={onEntrar} /></ProvedorAvisos>);

describe("Login", () => {
  it("mostra que a API está online", async () => {
    mockApi({ "GET /health": { body: { status: "ok" } } });
    tela();
    expect(await screen.findByText("API online")).toBeInTheDocument();
  });

  it("faz login, salva a sessão e entra", async () => {
    const m = mockApi({ "GET /health": { body: { status: "ok" } }, "POST /auth/login": { body: { access_token: "t", token_type: "bearer", usuario: USUARIO } } });
    const onEntrar = vi.fn();
    tela(onEntrar);
    await userEvent.type(screen.getByLabelText("E-mail"), "ana@studio.com");
    await userEvent.type(screen.getByLabelText("Senha"), "senha-forte-123");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(onEntrar).toHaveBeenCalledWith(USUARIO);
    expect(m.de("POST", "/auth/login")[0].body).toEqual({ email: "ana@studio.com", senha: "senha-forte-123" });
    expect(sessao.token()).toBe("t");
  });

  it("cadastra um novo estúdio", async () => {
    const m = mockApi({ "GET /health": { body: { status: "ok" } }, "POST /auth/registrar": { status: 201, body: { access_token: "t", token_type: "bearer", usuario: USUARIO } } });
    tela();
    await userEvent.click(screen.getByRole("tab", { name: "Criar estúdio" }));
    await userEvent.type(screen.getByLabelText("Nome do estúdio"), "Studio Equilíbrio");
    await userEvent.type(screen.getByLabelText("Seu nome"), "Ana");
    await userEvent.type(screen.getByLabelText("E-mail"), "ana@studio.com");
    await userEvent.type(screen.getByLabelText(/Senha/), "senha-forte-123");
    await userEvent.click(screen.getByRole("button", { name: "Criar estúdio e entrar" }));
    expect(m.de("POST", "/auth/registrar")[0].body).toEqual({ nome_estudio: "Studio Equilíbrio", nome: "Ana", email: "ana@studio.com", senha: "senha-forte-123" });
  });

  it("mostra a mensagem de erro da API", async () => {
    mockApi({ "GET /health": { body: { status: "ok" } }, "POST /auth/login": { status: 401, body: { detail: "E-mail ou senha incorretos." } } });
    const onEntrar = vi.fn();
    tela(onEntrar);
    await userEvent.type(screen.getByLabelText("E-mail"), "ana@studio.com");
    await userEvent.type(screen.getByLabelText("Senha"), "errada");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("E-mail ou senha incorretos.")).toBeInTheDocument();
    expect(onEntrar).not.toHaveBeenCalled();
  });
});
