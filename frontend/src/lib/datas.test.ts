import { describe, expect, it } from "vitest";
import { chaveDia, fmtDataPura, fmtDiaLongo, fmtHora, fmtMoeda, inicioDaSemana, isoDataHora, setFuso } from "./datas";

describe("datas no fuso do estúdio (navegador em UTC)", () => {
  it("converte 07:00 de São Paulo para 10:00 UTC", () => {
    expect(isoDataHora("2026-12-01", "07:00")).toBe("2026-12-01T10:00:00.000Z");
  });

  it("respeita outro fuso do estúdio (Manaus = UTC-4)", () => {
    setFuso("America/Manaus");
    expect(isoDataHora("2026-12-01", "07:00")).toBe("2026-12-01T11:00:00.000Z");
  });

  it("exibe o horário no fuso do estúdio, não no do navegador", () => {
    expect(fmtHora("2026-12-01T10:00:00Z")).toBe("07:00");
  });

  it("agrupa a aula no dia certo do estúdio (23h em SP já é outro dia em UTC)", () => {
    expect(chaveDia("2026-12-02T02:00:00Z")).toBe("2026-12-01");
  });

  it("ida e volta: o que digito é o que aparece", () => {
    const iso = isoDataHora("2026-11-30", "18:30");
    expect(fmtHora(iso)).toBe("18:30");
    expect(chaveDia(iso)).toBe("2026-11-30");
  });

  it("semana começa na segunda", () => {
    const seg = inicioDaSemana(new Date(2026, 10, 19)); // quinta 19/11/2026
    expect(seg.getDay()).toBe(1);
    expect(seg.getDate()).toBe(16);
  });

  it("formata textos em pt-BR", () => {
    expect(fmtDiaLongo("2026-11-23T13:00:00Z")).toBe("Segunda-feira, 23 de novembro");
    expect(fmtDataPura("2026-12-01")).toBe("01/12/2026");
    expect(fmtMoeda("350.5").replace(/\s/g, " ")).toBe("R$ 350,50");
  });
});
