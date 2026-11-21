import { Loader2, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { ApiError } from "../lib/api";

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

/* ---------- Botões e campos ---------- */

type Variante = "primario" | "secundario" | "perigo" | "fantasma";
const VARIANTES: Record<Variante, string> = {
  primario: "bg-brand-600 text-white hover:bg-brand-700 shadow-sm",
  secundario: "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50",
  perigo: "bg-red-600 text-white hover:bg-red-700",
  fantasma: "text-slate-600 hover:bg-slate-100",
};

export function Botao({
  variante = "primario", carregando, className, children, tamanho = "md", ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variante?: Variante; carregando?: boolean; tamanho?: "sm" | "md" }) {
  return (
    <button
      {...props}
      disabled={props.disabled || carregando}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer",
        tamanho === "sm" ? "px-3 py-1.5 text-sm" : "px-4 py-2.5 text-sm",
        VARIANTES[variante], className,
      )}
    >
      {carregando && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

const CAMPO = "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-100 disabled:bg-slate-50";

export const Input = (p: React.InputHTMLAttributes<HTMLInputElement>) => <input {...p} className={cx(CAMPO, p.className)} />;
export const Select = (p: React.SelectHTMLAttributes<HTMLSelectElement>) => <select {...p} className={cx(CAMPO, p.className)} />;
export const Textarea = (p: React.TextareaHTMLAttributes<HTMLTextAreaElement>) => <textarea {...p} className={cx(CAMPO, "min-h-28", p.className)} />;

export function Campo({ rotulo, dica, children, className }: { rotulo: string; dica?: string; children: ReactNode; className?: string }) {
  return (
    <div className={cx("space-y-1.5", className)}>
      {/* A dica fica FORA do label: o nome acessível do campo é só o rótulo. */}
      <label className="block space-y-1.5">
        <span className="text-sm font-medium text-slate-700">{rotulo}</span>
        {children}
      </label>
      {dica && <span className="block text-xs text-slate-500">{dica}</span>}
    </div>
  );
}

export function Interruptor({ marcado, onChange, rotulo, desabilitado }: { marcado: boolean; onChange: (v: boolean) => void; rotulo: string; desabilitado?: boolean }) {
  return (
    <label className={cx("flex items-center gap-3 text-sm", desabilitado ? "opacity-50" : "cursor-pointer")}>
      <button
        type="button" role="switch" aria-checked={marcado} disabled={desabilitado} onClick={() => onChange(!marcado)}
        className={cx("relative h-6 w-11 rounded-full transition", marcado ? "bg-brand-600" : "bg-slate-300")}
      >
        <span className={cx("absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition", marcado ? "left-5.5" : "left-0.5")} />
      </button>
      {rotulo}
    </label>
  );
}

/* ---------- Exibição ---------- */

const CORES = {
  cinza: "bg-slate-100 text-slate-700",
  verde: "bg-emerald-100 text-emerald-800",
  azul: "bg-sky-100 text-sky-800",
  laranja: "bg-amber-100 text-amber-800",
  vermelho: "bg-red-100 text-red-700",
  marca: "bg-brand-100 text-brand-800",
  roxo: "bg-violet-100 text-violet-800",
};
export type Cor = keyof typeof CORES;
export const Selo = ({ cor = "cinza", children, className }: { cor?: Cor; children: ReactNode; className?: string }) => (
  <span className={cx("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold", CORES[cor], className)}>{children}</span>
);

export const Cartao = ({ children, className, ...p }: React.HTMLAttributes<HTMLDivElement>) => (
  <div {...p} className={cx("rounded-2xl border border-slate-200 bg-white shadow-sm", className)}>{children}</div>
);

export const Carregando = ({ texto = "Carregando..." }: { texto?: string }) => (
  <div className="flex items-center justify-center gap-2 py-12 text-slate-500"><Loader2 className="h-5 w-5 animate-spin" />{texto}</div>
);

export function Vazio({ icone, titulo, texto, acao }: { icone?: ReactNode; titulo: string; texto?: string; acao?: ReactNode }) {
  return (
    <div className="rounded-2xl border-2 border-dashed border-slate-200 bg-white px-6 py-12 text-center">
      {icone && <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600">{icone}</div>}
      <p className="font-semibold text-slate-700">{titulo}</p>
      {texto && <p className="mt-1 text-sm text-slate-500">{texto}</p>}
      {acao && <div className="mt-4">{acao}</div>}
    </div>
  );
}

export const Erro = ({ texto, tentar }: { texto: string; tentar?: () => void }) => (
  <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
    {texto} {tentar && <button className="ml-2 font-semibold underline" onClick={tentar}>Tentar de novo</button>}
  </div>
);

export function Abas<T extends string>({ abas, ativa, onChange }: { abas: { id: T; rotulo: string }[]; ativa: T; onChange: (t: T) => void }) {
  return (
    <div role="tablist" className="flex gap-1 rounded-xl bg-slate-100 p-1">
      {abas.map((a) => (
        <button
          key={a.id} type="button" role="tab" aria-selected={ativa === a.id} onClick={() => onChange(a.id)}
          className={cx("flex-1 rounded-lg px-3 py-2 text-sm font-medium transition cursor-pointer", ativa === a.id ? "bg-white text-brand-700 shadow-sm" : "text-slate-600 hover:text-slate-800")}
        >
          {a.rotulo}
        </button>
      ))}
    </div>
  );
}

/* ---------- Modal ---------- */

export function Modal({ aberto, onFechar, titulo, subtitulo, children, largura = "max-w-lg" }: {
  aberto: boolean; onFechar: () => void; titulo: ReactNode; subtitulo?: ReactNode; children: ReactNode; largura?: string;
}) {
  useEffect(() => {
    if (!aberto) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onFechar();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [aberto, onFechar]);
  if (!aberto) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-slate-900/40 backdrop-blur-[2px] sm:items-center sm:p-4" onMouseDown={onFechar}>
      <div
        role="dialog" aria-modal="true" onMouseDown={(e) => e.stopPropagation()}
        className={cx("animate-entrar max-h-[92vh] w-full overflow-y-auto rounded-t-3xl bg-white p-5 shadow-xl sm:rounded-3xl sm:p-6", largura)}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{titulo}</h2>
            {subtitulo && <div className="mt-0.5 text-sm text-slate-500">{subtitulo}</div>}
          </div>
          <button onClick={onFechar} className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 cursor-pointer" aria-label="Fechar"><X className="h-5 w-5" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

/* ---------- Avisos (toasts) e confirmação ---------- */

type Aviso = { id: number; tipo: "sucesso" | "erro" | "alerta"; texto: string; detalhe?: string };
type Ctx = { avisar: (tipo: Aviso["tipo"], texto: string, detalhe?: string) => void; erro: (e: unknown) => void; confirmar: (c: Confirmacao) => void };
type Confirmacao = { titulo: string; texto?: string; botao?: string; perigo?: boolean; acao: () => void | Promise<void> };

const AvisosCtx = createContext<Ctx | null>(null);
export const useAvisos = () => useContext(AvisosCtx)!;

export function ProvedorAvisos({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const [conf, setConf] = useState<Confirmacao | null>(null);
  const [confirmando, setConfirmando] = useState(false);

  const avisar = useCallback((tipo: Aviso["tipo"], texto: string, detalhe?: string) => {
    const id = Date.now() + Math.random();
    setAvisos((a) => [...a, { id, tipo, texto, detalhe }]);
    setTimeout(() => setAvisos((a) => a.filter((x) => x.id !== id)), tipo === "erro" ? 7000 : 4500);
  }, []);
  const erro = useCallback((e: unknown) => {
    if (e instanceof ApiError) avisar("erro", e.message, e.traceId ? `Código de rastreio: ${e.traceId}` : undefined);
    else avisar("erro", e instanceof Error ? e.message : "Erro inesperado");
  }, [avisar]);

  const estilo = { sucesso: "border-emerald-200 bg-emerald-50 text-emerald-900", erro: "border-red-200 bg-red-50 text-red-900", alerta: "border-amber-200 bg-amber-50 text-amber-900" };

  return (
    <AvisosCtx.Provider value={{ avisar, erro, confirmar: setConf }}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-3 z-50 flex flex-col items-center gap-2 px-3 sm:items-end sm:pr-5">
        {avisos.map((a) => (
          <div key={a.id} role="status" className={cx("animate-entrar pointer-events-auto w-full max-w-sm rounded-2xl border px-4 py-3 text-sm shadow-lg", estilo[a.tipo])}>
            <p className="font-medium">{a.texto}</p>
            {a.detalhe && <p className="mt-0.5 text-xs opacity-75">{a.detalhe}</p>}
          </div>
        ))}
      </div>
      <Modal aberto={!!conf} onFechar={() => !confirmando && setConf(null)} titulo={conf?.titulo} largura="max-w-md">
        {conf?.texto && <p className="mb-5 text-sm text-slate-600">{conf.texto}</p>}
        <div className="flex justify-end gap-2">
          <Botao variante="secundario" onClick={() => setConf(null)} disabled={confirmando}>Voltar</Botao>
          <Botao
            variante={conf?.perigo ? "perigo" : "primario"} carregando={confirmando}
            onClick={async () => {
              if (!conf) return;
              setConfirmando(true);
              try { await conf.acao(); } finally { setConfirmando(false); setConf(null); }
            }}
          >
            {conf?.botao ?? "Confirmar"}
          </Botao>
        </div>
      </Modal>
    </AvisosCtx.Provider>
  );
}
