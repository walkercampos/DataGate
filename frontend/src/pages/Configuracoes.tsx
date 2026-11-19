import { CalendarRange, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { Botao, Campo, Cartao, Carregando, Input, Select, useAvisos } from "../components/ui";
import { api } from "../lib/api";
import { setFuso } from "../lib/datas";
import { useApi } from "../lib/hooks";
import type { Estudio, Grade } from "../lib/types";

const FUSOS = ["America/Sao_Paulo", "America/Manaus", "America/Cuiaba", "America/Belem", "America/Fortaleza", "America/Recife", "America/Bahia", "America/Porto_Velho", "America/Rio_Branco", "America/Noronha"];

export default function Configuracoes() {
  const q = useApi<Estudio>("/estudio");
  const [f, setF] = useState<Estudio | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [mes, setMes] = useState(() => { const d = new Date(); d.setMonth(d.getMonth() + 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; });
  const [gerando, setGerando] = useState(false);
  const { avisar, erro } = useAvisos();
  useEffect(() => { if (q.data) setF(q.data); }, [q.data]);

  if (!f) return <Carregando />;
  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    try {
      const r = await api<Estudio>("/estudio", { method: "PATCH", body: { nome: f.nome, capacidade_padrao_turma: f.capacidade_padrao_turma, antecedencia_cancelamento_horas: f.antecedencia_cancelamento_horas, validade_credito_dias: f.validade_credito_dias, fuso_horario: f.fuso_horario } });
      setF(r); setFuso(r.fuso_horario); avisar("sucesso", "Configurações salvas");
    } catch (e) { erro(e); } finally { setSalvando(false); }
  };
  const gerar = async () => {
    const [ano, m] = mes.split("-").map(Number);
    setGerando(true);
    try {
      const r = await api<Grade[]>("/contratos/gerar-grade-mensal", { method: "POST", body: { ano, mes: m } });
      const ag = r.reduce((s, g) => s + g.agendadas, 0);
      const lot = r.reduce((s, g) => s + g.lotadas.length, 0);
      avisar(lot ? "alerta" : "sucesso", `${r.length} contrato(s): ${ag} aula(s) agendada(s)${lot ? `, ${lot} em turma lotada` : ""}.`);
    } catch (e) { erro(e); } finally { setGerando(false); }
  };
  const num = (k: keyof Estudio) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: +e.target.value });

  return (
    <div className="max-w-2xl space-y-5">
      <h1 className="text-2xl font-bold text-slate-900">Configurações do estúdio</h1>
      <Cartao className="p-6">
        <form onSubmit={salvar} className="space-y-4">
          <Campo rotulo="Nome do estúdio"><Input required minLength={2} value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} /></Campo>
          <div className="grid gap-4 sm:grid-cols-3">
            <Campo rotulo="Alunos por turma" dica="Vale para novas aulas"><Input type="number" min={1} max={50} value={f.capacidade_padrao_turma} onChange={num("capacidade_padrao_turma")} /></Campo>
            <Campo rotulo="Antecedência (horas)" dica="Mínimo para cancelar com crédito"><Input type="number" min={0} max={168} value={f.antecedencia_cancelamento_horas} onChange={num("antecedencia_cancelamento_horas")} /></Campo>
            <Campo rotulo="Validade do crédito (dias)"><Input type="number" min={1} max={365} value={f.validade_credito_dias} onChange={num("validade_credito_dias")} /></Campo>
          </div>
          <Campo rotulo="Fuso horário">
            <Select value={f.fuso_horario} onChange={(e) => setF({ ...f, fuso_horario: e.target.value })}>
              {[...new Set([f.fuso_horario, ...FUSOS])].map((z) => <option key={z} value={z}>{z.replace("America/", "").replace("_", " ")}</option>)}
            </Select>
          </Campo>
          <div className="rounded-xl bg-brand-50 p-4 text-sm text-brand-900">
            📌 Alunos que cancelam com <b>{f.antecedencia_cancelamento_horas}h</b> ou mais de antecedência ganham <b>1 crédito de reposição</b> válido por <b>{f.validade_credito_dias} dias</b>.
            Cancelamentos fora do prazo ou faltas perdem a aula. Cada turma comporta <b>{f.capacidade_padrao_turma}</b> aluno(s).
          </div>
          <Botao type="submit" carregando={salvando}><Save className="h-4 w-4" /> Salvar</Botao>
        </form>
      </Cartao>

      <Cartao className="space-y-3 p-6">
        <p className="font-semibold text-slate-900">Grade fixa mensal</p>
        <p className="text-sm text-slate-500">Agenda todos os alunos com contrato ativo nos seus horários fixos do mês escolhido. Pode rodar mais de uma vez: nada é duplicado.</p>
        <div className="flex flex-wrap items-end gap-3">
          <Campo rotulo="Mês"><Input type="month" value={mes} onChange={(e) => setMes(e.target.value)} /></Campo>
          <Botao onClick={gerar} carregando={gerando}><CalendarRange className="h-4 w-4" /> Gerar grade do mês</Botao>
        </div>
      </Cartao>
    </div>
  );
}
