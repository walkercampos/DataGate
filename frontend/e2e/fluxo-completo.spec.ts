import { expect, test, type Page } from "@playwright/test";

const aviso = (p: Page, texto: string | RegExp) => expect(p.getByRole("status").filter({ hasText: texto }).first()).toBeVisible();

test("fluxo completo do estúdio", async ({ page: p }) => {
  const erros: string[] = [];
  p.on("pageerror", (e) => erros.push(e.message));
  p.on("console", (m) => m.type() === "error" && erros.push(m.text()));

  await test.step("cadastro do estúdio", async () => {
    await p.goto("/");
    await expect(p.getByText("API online")).toBeVisible();
    await p.getByRole("tab", { name: "Criar estúdio" }).click();
    await p.getByLabel("Nome do estúdio").fill("Studio Equilíbrio");
    await p.getByLabel("Seu nome").fill("Ana Souza");
    await p.getByLabel("E-mail").fill(`ana${Date.now()}@equilibrio.com.br`);
    await p.getByLabel("Senha").fill("senha-forte-123");
    await p.getByRole("button", { name: "Criar estúdio e entrar" }).click();
    await expect(p.getByRole("heading", { name: "Agenda" })).toBeVisible();
  });

  await test.step("plano 2x por semana", async () => {
    await p.getByRole("button", { name: "Planos" }).first().click();
    await p.getByRole("button", { name: "Novo plano" }).click();
    await p.getByLabel("Nome").fill("2x por semana");
    await p.getByLabel("Aulas por semana").fill("2");
    await p.getByLabel("Valor mensal (R$)").fill("350,00");
    await p.getByRole("button", { name: "Salvar" }).click();
    await aviso(p, "Plano criado!");
    await expect(p.getByText("R$ 350,00")).toBeVisible();
  });

  await test.step("cadastro de alunos", async () => {
    for (const [nome, tel] of [["Bruno Lima", "11912345678"], ["Maria Souza", "11987654321"]]) {
      await p.getByRole("button", { name: "Alunos" }).first().click();
      await p.getByRole("button", { name: "Novo aluno" }).click();
      await p.getByLabel("Nome completo").fill(nome);
      await p.getByLabel("Telefone (WhatsApp)").fill(tel);
      await p.getByRole("button", { name: "Salvar" }).click();
      await expect(p.getByRole("heading", { name: nome })).toBeVisible();
    }
  });

  await test.step("contrato com grade fixa (Maria)", async () => {
    await p.getByRole("button", { name: "Contratar plano" }).click();
    await p.getByLabel("Plano").selectOption({ label: "2x por semana — 2x/semana — R$ 350,00" });
    await p.getByRole("button", { name: "Contratar e gerar grade" }).click();
    await aviso(p, /Plano contratado!/);
    await expect(p.getByText("Segunda · 07:00")).toBeVisible();
    await p.getByRole("button", { name: "Gerar grade do próximo mês" }).click();
    await aviso(p, /Grade de \d\d\/\d{4}/);
  });

  await test.step("prontuário: rascunho, assinatura e verificação", async () => {
    await p.getByRole("tab", { name: "Prontuário" }).click();
    await p.getByRole("button", { name: "Novo registro" }).click();
    await p.getByRole("textbox", { name: /^Avaliação/ }).fill("Queixa: lombalgia há 6 meses.\nObjetivo: fortalecer core.");
    await p.getByRole("button", { name: "6", exact: true }).click();
    await p.getByRole("button", { name: "Salvar rascunho" }).click();
    await p.getByRole("button", { name: "Assinar", exact: true }).click();
    await p.getByRole("dialog").getByRole("button", { name: "Assinar" }).click();
    await aviso(p, "Registro assinado e bloqueado.");
    await expect(p.getByText(/SHA-256: [0-9a-f]{64}/)).toBeVisible();
    // Assinado = somente leitura: sem Assinar/Excluir/Editar no registro.
    await expect(p.getByRole("button", { name: "Excluir", exact: true })).toHaveCount(0);
    await expect(p.getByRole("button", { name: "Assinar", exact: true })).toHaveCount(0);
    await p.getByRole("button", { name: "Verificar integridade" }).click();
    await expect(p.getByText("Íntegro", { exact: true })).toBeVisible();
  });

  await test.step("agenda: horário no fuso do estúdio, aula avulsa, agendar e cancelar com crédito", async () => {
    await p.getByRole("button", { name: "Agenda" }).first().click();
    await p.getByLabel("Próxima semana").click();
    await expect(p.locator("main").getByText("07:00").first()).toBeVisible();

    await p.getByRole("button", { name: "Nova aula" }).click();
    await p.getByRole("dialog").getByLabel("Hora").fill("18:30");
    await p.getByRole("button", { name: "Criar aula" }).click();
    await aviso(p, "Aula criada!");
    await expect(p.locator("main").getByText("18:30")).toBeVisible();

    await p.locator('main button:has-text("07:00")').first().click();
    await p.getByRole("dialog").getByRole("combobox").selectOption({ label: "Bruno Lima" });
    await p.getByRole("button", { name: "Agendar" }).click();
    await expect(p.getByRole("dialog").getByRole("link", { name: "Bruno Lima" })).toBeVisible();
    await p.getByRole("dialog").getByRole("button", { name: "Cancelar" }).first().click();
    await p.getByRole("button", { name: "Cancelar agendamento" }).click();
    await aviso(p, /\+1 crédito de reposição/);
    await expect(p.getByText("Cancelou · crédito gerado")).toBeVisible();
  });

  await test.step("atendimento individual já com o paciente", async () => {
    await p.keyboard.press("Escape");
    await p.getByRole("button", { name: "Nova aula" }).click();
    await p.getByRole("radio", { name: /Individual/ }).click();
    await p.getByRole("dialog").getByLabel("Hora").fill("10:00");
    await p.getByLabel("Paciente (opcional)").selectOption({ label: "Bruno Lima" });
    await p.getByRole("button", { name: "Criar aula" }).click();
    await aviso(p, "Aula criada!");
    const card = p.locator('main button:has-text("10:00")');
    await expect(card.getByText("Individual", { exact: true })).toBeVisible();
    await expect(card.getByText("1/1")).toBeVisible();
  });

  await test.step("crédito aparece na ficha e é usado numa reposição", async () => {
    await p.locator('main button:has-text("18:30")').click();
    await p.getByRole("dialog").getByRole("combobox").selectOption({ label: "Maria Souza · 1 crédito(s)" });
    await p.getByRole("switch").click();
    await p.getByRole("button", { name: "Agendar" }).click();
    await aviso(p, /usando crédito de reposição/);
    await expect(p.getByRole("dialog").getByText("Reposição", { exact: true })).toBeVisible();
  });

  expect(erros).toEqual([]);
});
