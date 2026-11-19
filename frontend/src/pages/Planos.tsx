import { Plus, Tag } from "lucide-react";
import { useState } from "react";
import { Botao, Campo, Cartao, Carregando, Input, Interruptor, Modal, Selo, Vazio, cx, useAvisos } from "../components/ui";
import { api } from "../lib/api";
import { fmtMoeda } from "../lib/datas";
import { useApi } from "../lib/hooks";
import type { Plano } from "../lib/types";

export default function Planos() {
  const [inativos, setInativos] = useState(false);
  const q = useApi<Plano[]>("/planos", { apenas_ativos: !inativos });
  const [editando, setEditando] = useState<Plano | "novo" | null>(null);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Planos</h1>
          <p className="text-sm text-slate-500">Mudanças de preço valem só para novos contratos.</p>
        </div>
        <Botao onClick={() => setEditando("novo")}><Plus className="h-4 w-4" /> Novo plano</Botao>
      </div>
      <Interruptor marcado={inativos} onChange={setInativos} rotulo="Mostrar inativos" />
      {!q.data ? <Carregando /> : q.data.length === 0 ? (
        <Vazio icone={<Tag className="h-6 w-6" />} titulo="Nenhum plano" texto="Ex.: 1x por semana, 2x por semana, 3x por semana." acao={<Botao onClick={() => setEditando("novo")}>Criar plano</Botao>} />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {q.data.map((p) => (
            <button key={p.id} onClick={() => setEditando(p)} className="text-left cursor-pointer">
              <Cartao className={cx("p-5 transition hover:border-brand-300 hover:shadow-md", !p.ativo && "opacity-60")}>
                <div className="flex items-start justify-between">
                  <p className="font-semibold text-slate-900">{p.nome}</p>
                  {!p.ativo && <Selo>Inativo</Selo>}
                </div>
                <p className="mt-3 text-2xl font-bold text-brand-700">{fmtMoeda(p.valor_mensal)}<span className="text-sm font-normal text-slate-500">/mês</span></p>
                <p className="text-sm text-slate-500">{p.aulas_por_semana} aula{p.aulas_por_semana > 1 ? "s" : ""} por semana</p>
              </Cartao>
            </button>
          ))}
        </div>
      )}
      {editando && <FormPlano plano={editando === "novo" ? undefined : editando} onFechar={() => setEditando(null)} onSalvo={q.recarregar} />}
    </div>
  );
}

function FormPlano({ plano, onFechar, onSalvo }: { plano?: Plano; onFechar: () => void; onSalvo: () => void }) {
  const [f, setF] = useState({ nome: plano?.nome ?? "", aulas: plano?.aulas_por_semana ?? 2, valor: plano?.valor_mensal ?? "", ativo: plano?.ativo ?? true });
  const [enviando, setEnviando] = useState(false);
  const { avisar, erro } = useAvisos();

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    const corpo = { nome: f.nome, aulas_por_semana: f.aulas, valor_mensal: Number(String(f.valor).replace(",", ".")).toFixed(2) };
    try {
      if (plano) await api(`/planos/${plano.id}`, { method: "PATCH", body: { ...corpo, ativo: f.ativo } });
      else await api("/planos", { method: "POST", body: corpo });
      avisar("sucesso", plano ? "Plano atualizado" : "Plano criado!");
      onSalvo(); onFechar();
    } catch (e) { erro(e); } finally { setEnviando(false); }
  };

  return (
    <Modal aberto onFechar={onFechar} titulo={plano ? "Editar plano" : "Novo plano"} largura="max-w-md">
      <form onSubmit={salvar} className="space-y-4">
        <Campo rotulo="Nome"><Input required minLength={2} placeholder="Ex.: 2x por semana" value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} /></Campo>
        <div className="grid grid-cols-2 gap-4">
          <Campo rotulo="Aulas por semana"><Input type="number" min={1} max={7} required value={f.aulas} onChange={(e) => setF({ ...f, aulas: +e.target.value })} /></Campo>
          <Campo rotulo="Valor mensal (R$)"><Input required inputMode="decimal" placeholder="350,00" value={f.valor} onChange={(e) => setF({ ...f, valor: e.target.value })} /></Campo>
        </div>
        {plano && <Interruptor marcado={f.ativo} onChange={(v) => setF({ ...f, ativo: v })} rotulo="Plano ativo (disponível para novos contratos)" />}
        <Botao type="submit" className="w-full" carregando={enviando}>Salvar</Botao>
      </form>
    </Modal>
  );
}
