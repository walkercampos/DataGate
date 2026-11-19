import { ArrowLeft, Phone, Plus, Search, Ticket, UserRound, Users } from "lucide-react";
import { useState } from "react";
import { Abas, Botao, Campo, Cartao, Carregando, Erro, Input, Interruptor, Modal, Selo, Textarea, Vazio, cx, useAvisos } from "../components/ui";
import { api } from "../lib/api";
import { fmtData } from "../lib/datas";
import { useApi, useDebounce } from "../lib/hooks";
import type { Aluno } from "../lib/types";
import ContratoAluno from "./ContratoAluno";
import ProntuarioAluno from "./ProntuarioAluno";

export function mascaraTelefone(v: string) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d ? `(${d}` : "";
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

export default function Alunos({ alunoAberto, abrir }: { alunoAberto?: string; abrir: (id?: string) => void }) {
  if (alunoAberto) return <FichaAluno id={alunoAberto} voltar={() => abrir()} />;
  return <ListaAlunos abrir={abrir} />;
}

function ListaAlunos({ abrir }: { abrir: (id: string) => void }) {
  const [busca, setBusca] = useState("");
  const [inativos, setInativos] = useState(false);
  const [novo, setNovo] = useState(false);
  const termo = useDebounce(busca);
  const q = useApi<Aluno[]>("/alunos", { busca: termo, apenas_ativos: !inativos });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900">Alunos</h1>
        <Botao onClick={() => setNovo(true)}><Plus className="h-4 w-4" /> Novo aluno</Botao>
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative min-w-60 flex-1">
          <Search className="absolute top-3 left-3 h-4 w-4 text-slate-400" />
          <Input className="pl-9" placeholder="Buscar por nome ou telefone…" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </div>
        <Interruptor marcado={inativos} onChange={setInativos} rotulo="Mostrar inativos" />
      </div>

      {q.erro ? <Erro texto={q.erro} tentar={q.recarregar} /> : !q.data ? <Carregando /> : q.data.length === 0 ? (
        <Vazio icone={<Users className="h-6 w-6" />} titulo={termo ? "Nenhum aluno encontrado" : "Nenhum aluno cadastrado"} texto={termo ? "Tente outro termo de busca." : "Cadastre o primeiro aluno do estúdio."}
          acao={!termo && <Botao onClick={() => setNovo(true)}>Cadastrar aluno</Botao>} />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {q.data.map((a) => (
            <button key={a.id} onClick={() => abrir(a.id)} className="text-left cursor-pointer">
              <Cartao className={cx("p-4 transition hover:border-brand-300 hover:shadow-md", !a.ativo && "opacity-60")}>
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-100 font-semibold text-brand-700">{a.nome[0]?.toUpperCase()}</div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-slate-800">{a.nome}</p>
                    <p className="flex items-center gap-1 text-sm text-slate-500"><Phone className="h-3.5 w-3.5" />{a.telefone}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {!a.ativo && <Selo>Inativo</Selo>}
                      {a.creditos_reposicao > 0 && (
                        <Selo cor="roxo"><Ticket className="h-3 w-3" />{a.creditos_reposicao} reposição{a.creditos_reposicao > 1 ? "ões" : ""}</Selo>
                      )}
                    </div>
                  </div>
                </div>
              </Cartao>
            </button>
          ))}
        </div>
      )}
      <FormAluno aberto={novo} onFechar={() => setNovo(false)} onSalvo={(a) => { void q.recarregar(); abrir(a.id); }} />
    </div>
  );
}

function FormAluno({ aberto, onFechar, aluno, onSalvo }: { aberto: boolean; onFechar: () => void; aluno?: Aluno; onSalvo: (a: Aluno) => void }) {
  const vazio = { nome: "", telefone: "", email: "", observacoes: "", ativo: true };
  const [f, setF] = useState(aluno ? { nome: aluno.nome, telefone: aluno.telefone, email: aluno.email ?? "", observacoes: aluno.observacoes ?? "", ativo: aluno.ativo } : vazio);
  const [enviando, setEnviando] = useState(false);
  const { avisar, erro } = useAvisos();

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    // creditos_reposicao NUNCA é enviado: quem controla é o servidor.
    const corpo = { nome: f.nome, telefone: f.telefone, email: f.email || null, observacoes: f.observacoes || null, ...(aluno ? { ativo: f.ativo } : {}) };
    try {
      const r = aluno
        ? await api<Aluno>(`/alunos/${aluno.id}`, { method: "PATCH", body: corpo })
        : await api<Aluno>("/alunos", { method: "POST", body: corpo });
      avisar("sucesso", aluno ? "Dados atualizados" : "Aluno cadastrado!");
      if (!aluno) setF(vazio);
      onSalvo(r);
      onFechar();
    } catch (e) { erro(e); } finally { setEnviando(false); }
  };

  return (
    <Modal aberto={aberto} onFechar={onFechar} titulo={aluno ? "Editar aluno" : "Novo aluno"}>
      <form onSubmit={salvar} className="space-y-4">
        <Campo rotulo="Nome completo"><Input required minLength={2} value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} /></Campo>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Telefone (WhatsApp)"><Input required inputMode="tel" placeholder="(11) 98765-4321" value={f.telefone} onChange={(e) => setF({ ...f, telefone: mascaraTelefone(e.target.value) })} /></Campo>
          <Campo rotulo="E-mail (opcional)"><Input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Campo>
        </div>
        <Campo rotulo="Observações (opcional)"><Textarea value={f.observacoes} onChange={(e) => setF({ ...f, observacoes: e.target.value })} placeholder="Restrições, preferências…" /></Campo>
        {aluno && <Interruptor marcado={f.ativo} onChange={(v) => setF({ ...f, ativo: v })} rotulo="Aluno ativo" />}
        <Botao type="submit" className="w-full" carregando={enviando}>Salvar</Botao>
      </form>
    </Modal>
  );
}

function FichaAluno({ id, voltar }: { id: string; voltar: () => void }) {
  const q = useApi<Aluno>(`/alunos/${id}`);
  const [aba, setAba] = useState<"plano" | "prontuario" | "dados">("plano");
  const [editar, setEditar] = useState(false);
  const a = q.data;

  if (q.erro) return <div className="space-y-4"><Botao variante="fantasma" onClick={voltar}><ArrowLeft className="h-4 w-4" /> Alunos</Botao><Erro texto={q.erro} /></div>;
  if (!a) return <Carregando />;

  return (
    <div className="space-y-5">
      <Botao variante="fantasma" tamanho="sm" onClick={voltar}><ArrowLeft className="h-4 w-4" /> Alunos</Botao>
      <Cartao className="flex flex-wrap items-center gap-4 p-5">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-100 text-xl font-bold text-brand-700">{a.nome[0]?.toUpperCase()}</div>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-bold text-slate-900">{a.nome}</h1>
          <p className="text-sm text-slate-500">{a.telefone}{a.email ? ` · ${a.email}` : ""}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Selo cor={a.ativo ? "verde" : "cinza"}>{a.ativo ? "Ativo" : "Inativo"}</Selo>
            <Selo cor={a.creditos_reposicao > 0 ? "roxo" : "cinza"}>
              <Ticket className="h-3 w-3" />{a.creditos_reposicao} crédito(s) de reposição
              {a.creditos_reposicao > 0 && a.creditos_validade_ate && ` · até ${fmtData(a.creditos_validade_ate)}`}
            </Selo>
          </div>
        </div>
        <Botao variante="secundario" onClick={() => setEditar(true)}><UserRound className="h-4 w-4" /> Editar</Botao>
      </Cartao>

      <Abas abas={[{ id: "plano", rotulo: "Plano e horários" }, { id: "prontuario", rotulo: "Prontuário" }, { id: "dados", rotulo: "Observações" }]} ativa={aba} onChange={setAba} />
      {aba === "plano" && <ContratoAluno aluno={a} onMudou={q.recarregar} />}
      {aba === "prontuario" && <ProntuarioAluno aluno={a} />}
      {aba === "dados" && (
        <Cartao className="p-5 text-sm whitespace-pre-wrap text-slate-700">{a.observacoes || <span className="text-slate-400">Sem observações.</span>}</Cartao>
      )}
      {editar && <FormAluno aberto aluno={a} onFechar={() => setEditar(false)} onSalvo={(n) => q.setData(n)} />}
    </div>
  );
}
