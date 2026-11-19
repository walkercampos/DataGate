import { CalendarCheck, Plus, Repeat, X } from "lucide-react";
import { useState } from "react";
import { Botao, Campo, Cartao, Carregando, Input, Modal, Select, Selo, Vazio, useAvisos } from "../components/ui";
import { api } from "../lib/api";
import { DIAS_LONGOS, fmtDataHora, fmtDataPura, fmtMoeda, isoData } from "../lib/datas";
import { useApi } from "../lib/hooks";
import type { Aluno, Contrato, Grade, Plano } from "../lib/types";

const hora = (h: string) => h.slice(0, 5);

function resumoGrade(g: Grade) {
  const partes = [`${g.agendadas} aula(s) agendada(s)`];
  if (g.ja_existentes) partes.push(`${g.ja_existentes} já existiam`);
  if (g.lotadas.length) partes.push(`${g.lotadas.length} turma(s) lotada(s)`);
  return partes.join(" · ");
}

export default function ContratoAluno({ aluno, onMudou }: { aluno: Aluno; onMudou: () => void }) {
  const q = useApi<Contrato[]>("/contratos", { aluno_id: aluno.id });
  const [novo, setNovo] = useState(false);
  const [lotadas, setLotadas] = useState<string[]>([]);
  const { avisar, erro, confirmar } = useAvisos();

  if (!q.data) return <Carregando />;
  const ativo = q.data.find((c) => c.status === "ativo");
  const anteriores = q.data.filter((c) => c.status !== "ativo");

  const gerarProximoMes = async (c: Contrato) => {
    const d = new Date();
    const ano = d.getMonth() === 11 ? d.getFullYear() + 1 : d.getFullYear();
    const mes = d.getMonth() === 11 ? 1 : d.getMonth() + 2;
    try {
      const g = await api<Grade>(`/contratos/${c.id}/gerar-grade`, { method: "POST", body: { ano, mes } });
      setLotadas(g.lotadas);
      avisar(g.lotadas.length ? "alerta" : "sucesso", `Grade de ${String(mes).padStart(2, "0")}/${ano}: ${resumoGrade(g)}`);
    } catch (e) { erro(e); }
  };
  const encerrar = (c: Contrato) => confirmar({
    titulo: "Encerrar contrato?", perigo: true, botao: "Encerrar hoje",
    texto: "As aulas futuras deste contrato serão liberadas (sem gerar crédito de reposição).",
    acao: async () => {
      try {
        const r = await api<{ agendamentos_cancelados: number }>(`/contratos/${c.id}/encerrar`, { method: "POST", body: {} });
        avisar("sucesso", `Contrato encerrado. ${r.agendamentos_cancelados} aula(s) futura(s) liberada(s).`);
        void q.recarregar(); onMudou();
      } catch (e) { erro(e); }
    },
  });

  return (
    <div className="space-y-4">
      {ativo ? (
        <Cartao className="space-y-4 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm text-slate-500">Plano atual</p>
              <p className="text-lg font-semibold text-slate-900">{ativo.plano_nome}</p>
              <p className="text-sm text-slate-600">{ativo.aulas_por_semana}x por semana · {fmtMoeda(ativo.valor_mensal)}/mês · desde {fmtDataPura(ativo.data_inicio)}</p>
            </div>
            <Selo cor="verde">Ativo</Selo>
          </div>
          <div className="flex flex-wrap gap-2">
            {ativo.horarios.map((h) => (
              <span key={`${h.dia_semana}-${h.hora}`} className="rounded-xl bg-brand-50 px-3 py-1.5 text-sm font-medium text-brand-800">
                {DIAS_LONGOS[h.dia_semana]} · {hora(h.hora)}
              </span>
            ))}
          </div>
          {lotadas.length > 0 && (
            <div className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
              Turmas lotadas (não agendadas): {lotadas.map(fmtDataHora).join(", ")}
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <Botao variante="secundario" onClick={() => gerarProximoMes(ativo)}><Repeat className="h-4 w-4" /> Gerar grade do próximo mês</Botao>
            <Botao variante="fantasma" className="text-red-600" onClick={() => encerrar(ativo)}><X className="h-4 w-4" /> Encerrar contrato</Botao>
          </div>
        </Cartao>
      ) : (
        <Vazio icone={<CalendarCheck className="h-6 w-6" />} titulo="Sem plano ativo"
          texto="Contrate um plano com horários fixos: a grade do mês é gerada automaticamente."
          acao={aluno.ativo ? <Botao onClick={() => setNovo(true)}><Plus className="h-4 w-4" /> Contratar plano</Botao> : <p className="text-sm text-slate-500">Reative o aluno para contratar.</p>} />
      )}

      {anteriores.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-semibold text-slate-500">Contratos anteriores</p>
          {anteriores.map((c) => (
            <Cartao key={c.id} className="flex items-center justify-between p-3 text-sm">
              <span>{c.plano_nome} · {fmtMoeda(c.valor_mensal)}</span>
              <span className="text-slate-500">{fmtDataPura(c.data_inicio)} → {c.data_fim ? fmtDataPura(c.data_fim) : "—"}</span>
            </Cartao>
          ))}
        </div>
      )}

      {novo && <NovoContrato aluno={aluno} onFechar={() => setNovo(false)} onCriado={(g) => { setLotadas(g.lotadas); void q.recarregar(); onMudou(); }} />}
    </div>
  );
}

function NovoContrato({ aluno, onFechar, onCriado }: { aluno: Aluno; onFechar: () => void; onCriado: (g: Grade) => void }) {
  const planos = useApi<Plano[]>("/planos");
  const [planoId, setPlanoId] = useState("");
  const [inicio, setInicio] = useState(isoData(new Date()));
  const [horarios, setHorarios] = useState<{ dia_semana: number; hora: string }[]>([]);
  const [enviando, setEnviando] = useState(false);
  const { avisar, erro } = useAvisos();
  const plano = planos.data?.find((p) => p.id === planoId);

  const escolherPlano = (id: string) => {
    setPlanoId(id);
    const p = planos.data?.find((x) => x.id === id);
    const padrao = [0, 2, 4, 1, 3, 5, 6];
    setHorarios(p ? padrao.slice(0, p.aulas_por_semana).sort().map((d) => ({ dia_semana: d, hora: "07:00" })) : []);
  };

  const contratar = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    try {
      // Só IDs, data e horários: preço e frequência são lidos do plano pelo servidor.
      const r = await api<{ grade: Grade }>("/contratos", { method: "POST", body: { aluno_id: aluno.id, plano_id: planoId, data_inicio: inicio, horarios } });
      avisar(r.grade.lotadas.length ? "alerta" : "sucesso", `Plano contratado! ${resumoGrade(r.grade)}`);
      onCriado(r.grade);
      onFechar();
    } catch (e) { erro(e); } finally { setEnviando(false); }
  };

  return (
    <Modal aberto onFechar={onFechar} titulo="Contratar plano" subtitulo={aluno.nome}>
      {!planos.data ? <Carregando /> : planos.data.length === 0 ? (
        <Vazio titulo="Nenhum plano cadastrado" texto="Cadastre os planos do estúdio na tela Planos." acao={<a href="#/planos" className="font-semibold text-brand-700 underline">Ir para Planos</a>} />
      ) : (
        <form onSubmit={contratar} className="space-y-4">
          <Campo rotulo="Plano">
            <Select required value={planoId} onChange={(e) => escolherPlano(e.target.value)}>
              <option value="">Selecione…</option>
              {planos.data.map((p) => <option key={p.id} value={p.id}>{p.nome} — {p.aulas_por_semana}x/semana — {fmtMoeda(p.valor_mensal)}</option>)}
            </Select>
          </Campo>
          <Campo rotulo="Início"><Input type="date" required value={inicio} onChange={(e) => setInicio(e.target.value)} /></Campo>
          {plano && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-700">Horários fixos ({plano.aulas_por_semana} por semana)</p>
              {horarios.map((h, i) => (
                <div key={i} className="grid grid-cols-2 gap-2">
                  <Select value={h.dia_semana} onChange={(e) => setHorarios(horarios.map((x, j) => (j === i ? { ...x, dia_semana: +e.target.value } : x)))}>
                    {DIAS_LONGOS.map((d, n) => <option key={d} value={n}>{d}</option>)}
                  </Select>
                  <Input type="time" required value={h.hora} onChange={(e) => setHorarios(horarios.map((x, j) => (j === i ? { ...x, hora: e.target.value } : x)))} />
                </div>
              ))}
              <p className="text-xs text-slate-500">O aluno será agendado nesses horários em todas as semanas do mês. Se não houver aula no horário, ela é criada.</p>
            </div>
          )}
          <Botao type="submit" className="w-full" disabled={!plano} carregando={enviando}>Contratar e gerar grade</Botao>
        </form>
      )}
    </Modal>
  );
}
