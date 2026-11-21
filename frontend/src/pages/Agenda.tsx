import { CalendarPlus, ChevronLeft, ChevronRight, Clock, Repeat, Trash2, UserPlus } from "lucide-react";
import { useMemo, useState } from "react";
import { Abas, Botao, Campo, Carregando, Erro, Input, Interruptor, Modal, Select, Selo, Vazio, cx, useAvisos } from "../components/ui";
import { api } from "../lib/api";
import { DIAS_CURTOS, chaveDia, fmtDiaLongo, fmtDiaMes, fmtHora, inicioDaSemana, isoData, isoDataHora, mesmoDia, somarDias } from "../lib/datas";
import { useApi } from "../lib/hooks";
import { STATUS } from "../lib/status";
import type { Aluno, Aula, Cancelamento, TipoAula } from "../lib/types";

export default function Agenda() {
  const [ref, setRef] = useState(() => inicioDaSemana(new Date()));
  const [nova, setNova] = useState(false);
  const [aberta, setAberta] = useState<string | null>(null);
  const fim = somarDias(ref, 7);
  // Semana delimitada à meia-noite no fuso do estúdio.
  const q = useApi<Aula[]>("/agenda/aulas", { de: isoDataHora(isoData(ref), "00:00"), ate: isoDataHora(isoData(fim), "00:00") });
  const dias = useMemo(() => Array.from({ length: 7 }, (_, i) => somarDias(ref, i)), [ref]);
  const hoje = new Date();

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Agenda</h1>
          <p className="text-sm text-slate-500">{fmtDiaMes(ref)} – {fmtDiaMes(somarDias(ref, 6))} de {somarDias(ref, 6).getFullYear()}</p>
        </div>
        <div className="flex items-center gap-2">
          <Botao variante="secundario" tamanho="sm" onClick={() => setRef(somarDias(ref, -7))} aria-label="Semana anterior"><ChevronLeft className="h-4 w-4" /></Botao>
          <Botao variante="secundario" tamanho="sm" onClick={() => setRef(inicioDaSemana(new Date()))}>Hoje</Botao>
          <Botao variante="secundario" tamanho="sm" onClick={() => setRef(somarDias(ref, 7))} aria-label="Próxima semana"><ChevronRight className="h-4 w-4" /></Botao>
          <Botao onClick={() => setNova(true)}><CalendarPlus className="h-4 w-4" /> Nova aula</Botao>
        </div>
      </div>

      {q.erro ? <Erro texto={q.erro} tentar={q.recarregar} /> : q.carregando && !q.data ? <Carregando /> : q.data!.length === 0 ? (
        <Vazio icone={<CalendarPlus className="h-6 w-6" />} titulo="Nenhuma aula nesta semana" texto="Crie aulas avulsas ou gere uma grade recorrente para começar." acao={<Botao onClick={() => setNova(true)}>Criar aulas</Botao>} />
      ) : (
        <div className="grid gap-3 md:grid-cols-7">
          {dias.map((d) => {
            const aulas = q.data!.filter((a) => chaveDia(a.inicio) === isoData(d));
            const ehHoje = isoData(d) === chaveDia(hoje.toISOString());
            return (
              <div key={d.toISOString()} className={cx("space-y-2 rounded-2xl border bg-white p-2.5 md:min-h-56", ehHoje ? "border-brand-400 ring-2 ring-brand-100" : "border-slate-200")}>
                <p className={cx("px-1 text-xs font-bold uppercase tracking-wide", ehHoje ? "text-brand-700" : "text-slate-500")}>
                  {DIAS_CURTOS[(d.getDay() + 6) % 7]} {String(d.getDate()).padStart(2, "0")}/{String(d.getMonth() + 1).padStart(2, "0")}
                </p>
                {aulas.length === 0 && <p className="px-1 text-xs text-slate-300">—</p>}
                {aulas.map((a) => <CartaoAula key={a.id} aula={a} onClick={() => setAberta(a.id)} />)}
              </div>
            );
          })}
        </div>
      )}

      <NovaAula aberto={nova} onFechar={() => setNova(false)} dataPadrao={isoData(mesmoDia(ref, inicioDaSemana(hoje)) ? hoje : ref)} onCriado={q.recarregar} />
      {aberta && <DetalheAula id={aberta} onFechar={() => setAberta(null)} onMudou={q.recarregar} />}
    </div>
  );
}

function CartaoAula({ aula: a, onClick }: { aula: Aula; onClick: () => void }) {
  // Vermelho = turma lotada. Individual ocupado é o normal: fica na cor da marca.
  const lotada = a.tipo === "grupo" && a.vagas <= 0;
  const passou = new Date(a.inicio) < new Date();
  const ativos = a.participantes.filter((p) => STATUS[p.status].ativo);
  return (
    <button onClick={onClick} className={cx("w-full space-y-1.5 rounded-xl p-2.5 text-left transition hover:shadow-md cursor-pointer", passou ? "bg-slate-50 opacity-70" : "bg-brand-50 hover:bg-brand-100")}>
      <div className="flex items-center justify-between gap-1">
        <span className="flex items-center gap-1 text-xs font-bold text-brand-700"><Clock className="h-3 w-3" />{fmtHora(a.inicio)}</span>
        <span className={cx("rounded-full px-2 py-0.5 text-[11px] font-bold", lotada ? "bg-red-500 text-white" : "bg-white text-slate-700")}>{a.ocupadas}/{a.capacidade}</span>
      </div>
      <p className="text-sm font-semibold leading-tight text-slate-800">{a.titulo}</p>
      {a.tipo === "individual" && <Selo cor="roxo">Individual</Selo>}
      <div className="h-1 overflow-hidden rounded-full bg-white">
        <div className={cx("h-full", lotada ? "bg-red-500" : "bg-brand-500")} style={{ width: `${Math.min(100, (a.ocupadas / a.capacidade) * 100)}%` }} />
      </div>
      {ativos.length > 0 && <p className="line-clamp-3 text-xs text-slate-500">{ativos.map((p) => p.aluno_nome.split(" ")[0]).join(", ")}</p>}
    </button>
  );
}

/* ---------------- Nova aula (avulsa ou grade) ---------------- */

function NovaAula({ aberto, onFechar, dataPadrao, onCriado }: { aberto: boolean; onFechar: () => void; dataPadrao: string; onCriado: () => void }) {
  const [aba, setAba] = useState<"avulsa" | "grade">("avulsa");
  const [tipo, setTipo] = useState<TipoAula>("grupo");
  const [av, setAv] = useState({ data: "", hora: "07:00", duracao: 50, titulo: "Pilates", aluno: "" });
  const [gr, setGr] = useState({ data: "", semanas: 4, dias: [] as number[], hora: "07:00", duracao: 50, titulo: "Pilates" });
  const alunos = useApi<Aluno[]>(aberto && tipo === "individual" ? "/alunos" : null, { apenas_ativos: true });
  const mudarTipo = (t: TipoAula) => {
    setTipo(t);
    const titulo = t === "individual" ? "Atendimento individual" : "Pilates";
    setAv((x) => ({ ...x, titulo, aluno: "" }));
    setGr((x) => ({ ...x, titulo }));
  };
  const [enviando, setEnviando] = useState(false);
  const { avisar, erro } = useAvisos();

  const criar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (aba === "grade" && gr.dias.length === 0) return avisar("alerta", "Escolha pelo menos um dia da semana.");
    setEnviando(true);
    try {
      if (aba === "avulsa") {
        await api("/agenda/aulas", { method: "POST", body: { inicio: isoDataHora(av.data || dataPadrao, av.hora), duracao_minutos: av.duracao, titulo: av.titulo, tipo, ...(tipo === "individual" && av.aluno ? { aluno_id: av.aluno } : {}) } });
        avisar("sucesso", "Aula criada!");
      } else {
        const r = await api<Aula[]>("/agenda/aulas/recorrentes", {
          method: "POST",
          body: { data_inicio: gr.data || dataPadrao, semanas: gr.semanas, dias_semana: gr.dias, hora: gr.hora, duracao_minutos: gr.duracao, titulo: gr.titulo, tipo },
        });
        avisar(r.length ? "sucesso" : "alerta", r.length ? `${r.length} aulas criadas!` : "Nenhuma aula nova: os horários já existiam ou já passaram.");
      }
      onCriado();
      onFechar();
    } catch (e) { erro(e); } finally { setEnviando(false); }
  };

  return (
    <Modal aberto={aberto} onFechar={onFechar} titulo="Nova aula" subtitulo={tipo === "individual" ? "Atendimento individual: 1 paciente por horário." : "A capacidade da turma segue a configuração do estúdio."}>
      <Abas abas={[{ id: "avulsa", rotulo: "Avulsa" }, { id: "grade", rotulo: "Grade recorrente" }]} ativa={aba} onChange={setAba} />
      <div className="mt-4 grid grid-cols-2 gap-2" role="radiogroup" aria-label="Tipo de atendimento">
        {([["grupo", "👥 Turma", "várias pessoas por horário"], ["individual", "🧍 Individual", "1 paciente (fisio, avaliação)"]] as const).map(([t, rotulo, dica]) => (
          <button key={t} type="button" role="radio" aria-checked={tipo === t} onClick={() => mudarTipo(t)}
            className={cx("rounded-xl border p-3 text-left transition cursor-pointer", tipo === t ? "border-brand-500 bg-brand-50 ring-2 ring-brand-100" : "border-slate-200 hover:bg-slate-50")}>
            <span className="block text-sm font-semibold text-slate-800">{rotulo}</span>
            <span className="block text-xs text-slate-500">{dica}</span>
          </button>
        ))}
      </div>
      <form onSubmit={criar} className="mt-4 grid grid-cols-2 gap-3">
        {aba === "avulsa" ? (
          <>
            <Campo rotulo="Data"><Input type="date" required value={av.data || dataPadrao} onChange={(e) => setAv({ ...av, data: e.target.value })} /></Campo>
            <Campo rotulo="Hora"><Input type="time" required value={av.hora} onChange={(e) => setAv({ ...av, hora: e.target.value })} /></Campo>
            <Campo rotulo="Duração (min)"><Input type="number" min={10} max={240} value={av.duracao} onChange={(e) => setAv({ ...av, duracao: +e.target.value })} /></Campo>
            <Campo rotulo="Título"><Input required minLength={2} value={av.titulo} onChange={(e) => setAv({ ...av, titulo: e.target.value })} /></Campo>
            {tipo === "individual" && (
              <Campo rotulo="Paciente (opcional)" className="col-span-2" dica="Já agenda o paciente neste horário.">
                <Select value={av.aluno} onChange={(e) => setAv({ ...av, aluno: e.target.value })}>
                  <option value="">Deixar o horário livre</option>
                  {alunos.data?.map((al) => <option key={al.id} value={al.id}>{al.nome}</option>)}
                </Select>
              </Campo>
            )}
          </>
        ) : (
          <>
            <Campo rotulo="A partir de"><Input type="date" required value={gr.data || dataPadrao} onChange={(e) => setGr({ ...gr, data: e.target.value })} /></Campo>
            <Campo rotulo="Por quantas semanas"><Input type="number" min={1} max={12} value={gr.semanas} onChange={(e) => setGr({ ...gr, semanas: +e.target.value })} /></Campo>
            <div className="col-span-2 space-y-1.5">
              <span className="text-sm font-medium text-slate-700">Dias da semana</span>
              <div className="flex flex-wrap gap-2">
                {DIAS_CURTOS.map((d, i) => {
                  const on = gr.dias.includes(i);
                  return (
                    <button type="button" key={d} onClick={() => setGr({ ...gr, dias: on ? gr.dias.filter((x) => x !== i) : [...gr.dias, i] })}
                      className={cx("rounded-xl border px-3 py-1.5 text-sm font-medium transition cursor-pointer", on ? "border-brand-500 bg-brand-600 text-white" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50")}>
                      {d}
                    </button>
                  );
                })}
              </div>
            </div>
            <Campo rotulo="Hora"><Input type="time" required value={gr.hora} onChange={(e) => setGr({ ...gr, hora: e.target.value })} /></Campo>
            <Campo rotulo="Duração (min)"><Input type="number" min={10} max={240} value={gr.duracao} onChange={(e) => setGr({ ...gr, duracao: +e.target.value })} /></Campo>
            <Campo rotulo="Título" className="col-span-2"><Input required minLength={2} value={gr.titulo} onChange={(e) => setGr({ ...gr, titulo: e.target.value })} /></Campo>
          </>
        )}
        <Botao type="submit" className="col-span-2 mt-1" carregando={enviando}>{aba === "avulsa" ? "Criar aula" : <><Repeat className="h-4 w-4" /> Gerar grade</>}</Botao>
      </form>
    </Modal>
  );
}

/* ---------------- Detalhe da aula ---------------- */

function DetalheAula({ id, onFechar, onMudou }: { id: string; onFechar: () => void; onMudou: () => void }) {
  const q = useApi<Aula>(`/agenda/aulas/${id}`);
  const { avisar, erro, confirmar } = useAvisos();
  const a = q.data;
  const atualizar = () => { void q.recarregar(); onMudou(); };

  const presenca = async (ag: string, status: "presente" | "falta") => {
    try {
      await api(`/agenda/agendamentos/${ag}/presenca`, { method: "POST", body: { status } });
      avisar("sucesso", status === "presente" ? "Presença registrada" : "Falta registrada");
      atualizar();
    } catch (e) { erro(e); }
  };
  const cancelar = (ag: string, nome: string) => confirmar({
    titulo: `Cancelar a aula de ${nome}?`,
    texto: "Se o cancelamento respeitar a antecedência mínima do estúdio, o aluno ganha 1 crédito de reposição. Fora do prazo, a aula é perdida.",
    botao: "Cancelar agendamento", perigo: true,
    acao: async () => {
      try {
        const r = await api<Cancelamento>(`/agenda/agendamentos/${ag}/cancelar`, { method: "POST" });
        avisar(r.credito_gerado ? "sucesso" : "alerta", r.mensagem);
        atualizar();
      } catch (e) { erro(e); }
    },
  });
  const excluir = () => confirmar({
    titulo: "Excluir esta aula?", texto: "Só é possível excluir aulas que nunca tiveram agendamentos.", botao: "Excluir", perigo: true,
    acao: async () => {
      try { await api(`/agenda/aulas/${id}`, { method: "DELETE" }); avisar("sucesso", "Aula excluída"); onMudou(); onFechar(); } catch (e) { erro(e); }
    },
  });

  return (
    <Modal
      aberto onFechar={onFechar} titulo={a ? a.titulo : "Aula"}
      subtitulo={a && <span>{fmtDiaLongo(a.inicio)} · {fmtHora(a.inicio)} · {a.duracao_minutos} min</span>}
    >
      {!a ? <Carregando /> : (
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
            <span className="text-sm text-slate-600">{a.tipo === "individual" ? "Atendimento individual" : "Ocupação"}</span>
            <span className={cx("text-sm font-bold", a.vagas <= 0 ? "text-red-600" : "text-brand-700")}>
              {a.ocupadas}/{a.capacidade} · {a.vagas > 0 ? `${a.vagas} vaga${a.vagas > 1 ? "s" : ""}` : "lotada"}
            </span>
          </div>

          <div className="space-y-2">
            {a.participantes.length === 0 && <p className="rounded-2xl bg-slate-50 p-4 text-center text-sm text-slate-500">Nenhum aluno nesta aula ainda.</p>}
            {a.participantes.map((p) => {
              const s = STATUS[p.status];
              return (
                <div key={p.agendamento_id} className="rounded-2xl border border-slate-200 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <a href={`#/alunos/${p.aluno_id}`} className={cx("font-medium hover:underline", !s.ativo && "text-slate-400 line-through")}>{p.aluno_nome}</a>
                      {p.tipo === "reposicao" && <Selo cor="marca" className="ml-2">Reposição</Selo>}
                    </div>
                    <Selo cor={s.cor}>{s.rotulo}</Selo>
                  </div>
                  {p.status === "agendado" && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Botao tamanho="sm" variante="secundario" onClick={() => presenca(p.agendamento_id, "presente")}>✅ Presente</Botao>
                      <Botao tamanho="sm" variante="secundario" onClick={() => presenca(p.agendamento_id, "falta")}>⚠️ Falta</Botao>
                      <Botao tamanho="sm" variante="fantasma" className="text-red-600" onClick={() => cancelar(p.agendamento_id, p.aluno_nome)}>Cancelar</Botao>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {new Date(a.inicio) > new Date() && <AdicionarAluno aulaId={a.id} lotada={a.vagas <= 0} onAdicionado={atualizar} />}
          <Botao variante="fantasma" className="w-full text-red-600" onClick={excluir}><Trash2 className="h-4 w-4" /> Excluir aula</Botao>
        </div>
      )}
    </Modal>
  );
}

function AdicionarAluno({ aulaId, lotada, onAdicionado }: { aulaId: string; lotada: boolean; onAdicionado: () => void }) {
  const alunos = useApi<Aluno[]>("/alunos", { apenas_ativos: true });
  const [sel, setSel] = useState("");
  const [repo, setRepo] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const { avisar, erro } = useAvisos();
  const aluno = alunos.data?.find((x) => x.id === sel);
  const creditos = aluno?.creditos_reposicao ?? 0;

  const adicionar = async () => {
    setEnviando(true);
    try {
      await api(`/agenda/aulas/${aulaId}/agendamentos`, { method: "POST", body: { aluno_id: sel, usar_reposicao: repo } });
      avisar("sucesso", `${aluno?.nome} agendado(a)${repo ? " usando crédito de reposição" : ""}`);
      setSel(""); setRepo(false);
      void alunos.recarregar();
      onAdicionado();
    } catch (e) { erro(e); } finally { setEnviando(false); }
  };

  return (
    <div className="space-y-3 rounded-2xl bg-brand-50 p-4">
      <p className="flex items-center gap-2 text-sm font-semibold text-brand-800"><UserPlus className="h-4 w-4" /> Adicionar aluno</p>
      <Select value={sel} onChange={(e) => { setSel(e.target.value); setRepo(false); }}>
        <option value="">Selecione um aluno…</option>
        {alunos.data?.map((al) => (
          <option key={al.id} value={al.id}>{al.nome}{al.creditos_reposicao > 0 ? ` · ${al.creditos_reposicao} crédito(s)` : ""}</option>
        ))}
      </Select>
      <Interruptor
        marcado={repo} onChange={setRepo} desabilitado={!sel || creditos === 0}
        rotulo={sel ? `Usar crédito de reposição (${creditos} disponível${creditos === 1 ? "" : "is"})` : "Usar crédito de reposição"}
      />
      <Botao className="w-full" disabled={!sel} carregando={enviando} onClick={adicionar}>{lotada ? "Tentar agendar (turma lotada)" : "Agendar"}</Botao>
    </div>
  );
}

