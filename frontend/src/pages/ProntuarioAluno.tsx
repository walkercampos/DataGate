import { FilePlus2, Lock, PenLine, ShieldAlert, ShieldCheck, Trash2 } from "lucide-react";
import { useState } from "react";
import { Botao, Campo, Cartao, Carregando, Input, Modal, Select, Selo, Textarea, Vazio, cx, useAvisos } from "../components/ui";
import { api } from "../lib/api";
import { fmtDataHora } from "../lib/datas";
import { useApi } from "../lib/hooks";
import type { Aluno, Registro, Verificacao } from "../lib/types";

const TIPOS = { avaliacao: "Avaliação física", evolucao: "Evolução" } as const;

export default function ProntuarioAluno({ aluno }: { aluno: Aluno }) {
  const q = useApi<Registro[]>(`/alunos/${aluno.id}/prontuario`);
  const [editando, setEditando] = useState<Registro | "novo" | null>(null);
  const [verificacoes, setVerificacoes] = useState<Record<string, Verificacao>>({});
  const { avisar, erro, confirmar } = useAvisos();

  const assinar = (r: Registro) => confirmar({
    titulo: "Assinar este registro?", botao: "Assinar",
    texto: "Depois de assinado, o registro recebe um hash SHA-256 e fica bloqueado para sempre: não poderá ser editado nem excluído (exigência CFM/CREFITO/LGPD).",
    acao: async () => {
      try { await api(`/prontuario/${r.id}/assinar`, { method: "POST" }); avisar("sucesso", "Registro assinado e bloqueado."); void q.recarregar(); } catch (e) { erro(e); }
    },
  });
  const excluir = (r: Registro) => confirmar({
    titulo: "Excluir rascunho?", perigo: true, botao: "Excluir",
    acao: async () => {
      try { await api(`/prontuario/${r.id}`, { method: "DELETE" }); avisar("sucesso", "Rascunho excluído."); void q.recarregar(); } catch (e) { erro(e); }
    },
  });
  const verificar = async (r: Registro) => {
    try {
      const v = await api<Verificacao>(`/prontuario/${r.id}/verificar`);
      setVerificacoes((x) => ({ ...x, [r.id]: v }));
      avisar(v.integro ? "sucesso" : "erro", v.integro ? "Íntegro: o conteúdo é exatamente o que foi assinado." : "ATENÇÃO: o conteúdo não confere com o hash da assinatura!");
    } catch (e) { erro(e); }
  };

  if (!q.data) return <Carregando />;
  return (
    <div className="space-y-4">
      <div className="flex justify-end"><Botao onClick={() => setEditando("novo")}><FilePlus2 className="h-4 w-4" /> Novo registro</Botao></div>
      {q.data.length === 0 ? (
        <Vazio icone={<FilePlus2 className="h-6 w-6" />} titulo="Prontuário vazio" texto="Comece pela avaliação física inicial do aluno." />
      ) : q.data.map((r) => {
        const v = verificacoes[r.id];
        return (
          <Cartao key={r.id} className="space-y-3 p-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <Selo cor={r.tipo === "avaliacao" ? "marca" : "azul"}>{TIPOS[r.tipo]}</Selo>
                  {r.status === "assinado" ? <Selo cor="verde"><Lock className="h-3 w-3" /> Assinado</Selo> : <Selo cor="laranja">Rascunho</Selo>}
                  {r.dor_eva !== null && <Selo cor={r.dor_eva >= 7 ? "vermelho" : r.dor_eva >= 4 ? "laranja" : "verde"}>Dor {r.dor_eva}/10</Selo>}
                </div>
                <p className="mt-2 font-semibold text-slate-900">{r.titulo}</p>
                <p className="text-xs text-slate-500">Criado por {r.autor_nome} em {fmtDataHora(r.criado_em)}</p>
              </div>
            </div>
            <p className="text-sm whitespace-pre-wrap text-slate-700">{r.conteudo}</p>
            {r.status === "assinado" ? (
              <div className="space-y-2 rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
                <p>Assinado por <b>{r.assinado_por_nome}</b> em {r.assinado_em && fmtDataHora(r.assinado_em)}</p>
                <p className="font-mono break-all">SHA-256: {r.hash_sha256}</p>
                <div className="flex items-center gap-3">
                  <Botao tamanho="sm" variante="secundario" onClick={() => verificar(r)}><ShieldCheck className="h-4 w-4" /> Verificar integridade</Botao>
                  {v && (
                    <span className={cx("flex items-center gap-1 font-semibold", v.integro ? "text-emerald-700" : "text-red-700")}>
                      {v.integro ? <ShieldCheck className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}{v.integro ? "Íntegro" : "Adulterado!"}
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                <Botao tamanho="sm" variante="secundario" onClick={() => setEditando(r)}><PenLine className="h-4 w-4" /> Editar</Botao>
                <Botao tamanho="sm" onClick={() => assinar(r)}><Lock className="h-4 w-4" /> Assinar</Botao>
                <Botao tamanho="sm" variante="fantasma" className="text-red-600" onClick={() => excluir(r)}><Trash2 className="h-4 w-4" /> Excluir</Botao>
              </div>
            )}
          </Cartao>
        );
      })}
      {editando && (
        <FormRegistro aluno={aluno} registro={editando === "novo" ? undefined : editando} primeiro={q.data.length === 0}
          onFechar={() => setEditando(null)} onSalvo={() => void q.recarregar()} />
      )}
    </div>
  );
}

function FormRegistro({ aluno, registro, primeiro, onFechar, onSalvo }: { aluno: Aluno; registro?: Registro; primeiro: boolean; onFechar: () => void; onSalvo: () => void }) {
  const [f, setF] = useState({
    tipo: registro?.tipo ?? (primeiro ? "avaliacao" : "evolucao"),
    titulo: registro?.titulo ?? (primeiro ? "Avaliação física inicial" : "Evolução da sessão"),
    conteudo: registro?.conteudo ?? "",
    dor: registro?.dor_eva ?? null as number | null,
  });
  const [enviando, setEnviando] = useState(false);
  const { avisar, erro } = useAvisos();

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    try {
      if (registro) await api(`/prontuario/${registro.id}`, { method: "PATCH", body: { titulo: f.titulo, conteudo: f.conteudo, dor_eva: f.dor } });
      else await api(`/alunos/${aluno.id}/prontuario`, { method: "POST", body: { tipo: f.tipo, titulo: f.titulo, conteudo: f.conteudo, dor_eva: f.dor } });
      avisar("sucesso", "Rascunho salvo. Assine quando estiver pronto.");
      onSalvo(); onFechar();
    } catch (e) { erro(e); } finally { setEnviando(false); }
  };

  return (
    <Modal aberto onFechar={onFechar} titulo={registro ? "Editar rascunho" : "Novo registro"} subtitulo={aluno.nome} largura="max-w-2xl">
      <form onSubmit={salvar} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Tipo">
            <Select disabled={!!registro} value={f.tipo} onChange={(e) => setF({ ...f, tipo: e.target.value as typeof f.tipo })}>
              <option value="avaliacao">Avaliação física</option>
              <option value="evolucao">Evolução</option>
            </Select>
          </Campo>
          <Campo rotulo="Título"><Input required minLength={2} value={f.titulo} onChange={(e) => setF({ ...f, titulo: e.target.value })} /></Campo>
        </div>
        <Campo rotulo={f.tipo === "avaliacao" ? "Avaliação" : "Evolução"} dica={f.tipo === "avaliacao" ? "Queixa principal, histórico, testes, postura, objetivos…" : "Exercícios, resposta do paciente, ajustes…"}>
          <Textarea required className="min-h-40" value={f.conteudo} onChange={(e) => setF({ ...f, conteudo: e.target.value })} />
        </Campo>
        <div className="space-y-2">
          <span className="text-sm font-medium text-slate-700">Dor (escala EVA 0–10) <span className="font-normal text-slate-400">opcional</span></span>
          <div className="flex flex-wrap gap-1.5">
            {Array.from({ length: 11 }, (_, n) => (
              <button type="button" key={n} onClick={() => setF({ ...f, dor: f.dor === n ? null : n })}
                className={cx("h-9 w-9 rounded-lg border text-sm font-semibold transition cursor-pointer",
                  f.dor === n ? (n >= 7 ? "border-red-500 bg-red-500 text-white" : n >= 4 ? "border-amber-500 bg-amber-500 text-white" : "border-emerald-500 bg-emerald-500 text-white") : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50")}>
                {n}
              </button>
            ))}
          </div>
        </div>
        <Botao type="submit" className="w-full" carregando={enviando}>Salvar rascunho</Botao>
      </form>
    </Modal>
  );
}
