import { CalendarDays, LogOut, Settings, Tag, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { cx } from "./components/ui";
import { api, sessao, setOnUnauthorized } from "./lib/api";
import { setFuso } from "./lib/datas";
import type { Estudio, Usuario } from "./lib/types";
import Agenda from "./pages/Agenda";
import Alunos from "./pages/Alunos";
import Configuracoes from "./pages/Configuracoes";
import Login from "./pages/Login";
import Planos from "./pages/Planos";

const PAGINAS = [
  { id: "agenda", rotulo: "Agenda", icone: CalendarDays },
  { id: "alunos", rotulo: "Alunos", icone: Users },
  { id: "planos", rotulo: "Planos", icone: Tag },
  { id: "config", rotulo: "Configurações", icone: Settings },
] as const;
type Pagina = (typeof PAGINAS)[number]["id"];

const lerHash = (): { pagina: Pagina; param?: string } => {
  const [p, param] = window.location.hash.replace(/^#\/?/, "").split("/");
  return { pagina: (PAGINAS.some((x) => x.id === p) ? p : "agenda") as Pagina, param };
};

export default function App() {
  const [usuario, setUsuario] = useState<Usuario | null>(sessao.usuario());
  const [rota, setRota] = useState(lerHash);
  const [fusoPronto, setFusoPronto] = useState(false);

  const sair = useCallback(() => { sessao.limpar(); setUsuario(null); }, []);
  useEffect(() => { setOnUnauthorized(sair); }, [sair]);
  useEffect(() => {
    const f = () => setRota(lerHash());
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);

  // Carrega o fuso do estúdio antes de mostrar qualquer data.
  useEffect(() => {
    if (!usuario) { setFusoPronto(false); return; }
    api<Estudio>("/estudio").then((e) => setFuso(e.fuso_horario)).catch(() => {}).finally(() => setFusoPronto(true));
  }, [usuario]);

  if (!usuario || !sessao.token()) return <Login onEntrar={setUsuario} />;
  if (!fusoPronto) return null;

  const ir = (p: Pagina, param?: string) => { window.location.hash = `/${p}${param ? "/" + param : ""}`; };

  return (
    <div className="flex min-h-full">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-slate-200 bg-white p-4 md:flex">
        <div className="mb-6 flex items-center gap-2 px-2">
          <span className="text-2xl">🧘</span>
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-900">{usuario.estudio_nome}</p>
            <p className="text-xs text-slate-500">Studio Pilates</p>
          </div>
        </div>
        <nav className="space-y-1">
          {PAGINAS.map(({ id, rotulo, icone: Icone }) => (
            <button
              key={id} onClick={() => ir(id)}
              className={cx("flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition cursor-pointer",
                rota.pagina === id ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50")}
            >
              <Icone className="h-5 w-5" /> {rotulo}
            </button>
          ))}
        </nav>
        <div className="mt-auto border-t border-slate-100 pt-4">
          <p className="truncate px-2 text-sm font-medium text-slate-700">{usuario.nome}</p>
          <p className="truncate px-2 text-xs text-slate-500">{usuario.email}</p>
          <button onClick={sair} className="mt-3 flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 cursor-pointer">
            <LogOut className="h-4 w-4" /> Sair
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur md:hidden">
          <span className="font-semibold">🧘 {usuario.estudio_nome}</span>
          <button onClick={sair} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="Sair"><LogOut className="h-5 w-5" /></button>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 pb-28 md:px-8 md:pb-10">
          {rota.pagina === "agenda" && <Agenda />}
          {rota.pagina === "alunos" && <Alunos alunoAberto={rota.param} abrir={(id) => ir("alunos", id)} />}
          {rota.pagina === "planos" && <Planos />}
          {rota.pagina === "config" && <Configuracoes />}
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-slate-200 bg-white md:hidden">
        {PAGINAS.map(({ id, rotulo, icone: Icone }) => (
          <button key={id} onClick={() => ir(id)} className={cx("flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium", rota.pagina === id ? "text-brand-700" : "text-slate-500")}>
            <Icone className="h-5 w-5" /> {rotulo === "Configurações" ? "Ajustes" : rotulo}
          </button>
        ))}
      </nav>
    </div>
  );
}
