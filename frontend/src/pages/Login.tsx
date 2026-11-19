import { useEffect, useState } from "react";
import { Abas, Botao, Campo, Cartao, Input, cx, useAvisos } from "../components/ui";
import { api, sessao } from "../lib/api";
import type { AuthResp, Usuario } from "../lib/types";

export default function Login({ onEntrar }: { onEntrar: (u: Usuario) => void }) {
  const [aba, setAba] = useState<"entrar" | "criar">("entrar");
  const [f, setF] = useState({ nome_estudio: "", nome: "", email: "", senha: "" });
  const [enviando, setEnviando] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const { erro } = useAvisos();

  useEffect(() => {
    api<{ status: string }>("/health").then((r) => setOnline(r.status === "ok")).catch(() => setOnline(false));
  }, []);

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    try {
      const r = aba === "entrar"
        ? await api<AuthResp>("/auth/login", { method: "POST", body: { email: f.email, senha: f.senha } })
        : await api<AuthResp>("/auth/registrar", { method: "POST", body: f });
      sessao.salvar(r);
      onEntrar(r.usuario);
    } catch (e) {
      erro(e);
    } finally {
      setEnviando(false);
    }
  };
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  return (
    <div className="flex min-h-full items-center justify-center bg-gradient-to-br from-brand-50 via-white to-brand-100 p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="text-5xl">🧘</div>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">Studio Pilates</h1>
          <p className="text-sm text-slate-500">Agenda, alunos e prontuário do seu estúdio</p>
        </div>
        <Cartao className="p-6">
          <Abas abas={[{ id: "entrar", rotulo: "Entrar" }, { id: "criar", rotulo: "Criar estúdio" }]} ativa={aba} onChange={setAba} />
          <form onSubmit={enviar} className="mt-5 space-y-4">
            {aba === "criar" && (
              <>
                <Campo rotulo="Nome do estúdio"><Input required minLength={2} value={f.nome_estudio} onChange={set("nome_estudio")} placeholder="Ex.: Studio Equilíbrio" /></Campo>
                <Campo rotulo="Seu nome"><Input required minLength={2} value={f.nome} onChange={set("nome")} placeholder="Ex.: Ana Souza" /></Campo>
              </>
            )}
            <Campo rotulo="E-mail"><Input type="email" required value={f.email} onChange={set("email")} autoComplete="email" placeholder="voce@estudio.com.br" /></Campo>
            <Campo rotulo="Senha" dica={aba === "criar" ? "Mínimo de 8 caracteres" : undefined}>
              <Input type="password" required minLength={aba === "criar" ? 8 : 1} value={f.senha} onChange={set("senha")} autoComplete={aba === "criar" ? "new-password" : "current-password"} />
            </Campo>
            <Botao type="submit" className="w-full" carregando={enviando}>{aba === "entrar" ? "Entrar" : "Criar estúdio e entrar"}</Botao>
          </form>
        </Cartao>
        <p className="mt-4 flex items-center justify-center gap-2 text-xs text-slate-500">
          <span className={cx("h-2 w-2 rounded-full", online === null ? "bg-slate-300" : online ? "bg-emerald-500" : "bg-red-500")} />
          {online === null ? "Verificando API..." : online ? "API online" : "API offline — rode: docker compose up -d"}
        </p>
      </div>
    </div>
  );
}
