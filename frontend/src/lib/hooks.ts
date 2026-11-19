import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

/** Carrega dados da API e expõe recarregar(). Refaz a busca quando `deps` mudam. */
export function useApi<T>(path: string | null, query?: Record<string, unknown>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(!!path);
  const seq = useRef(0);

  const recarregar = useCallback(async () => {
    if (!path) return;
    const atual = ++seq.current;
    setCarregando(true);
    try {
      const r = await api<T>(path, { query });
      if (atual === seq.current) { setData(r); setErro(null); }
    } catch (e) {
      if (atual === seq.current) setErro((e as Error).message);
    } finally {
      if (atual === seq.current) setCarregando(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, JSON.stringify(query)]);

  useEffect(() => { void recarregar(); }, [recarregar, ...deps]);
  return { data, erro, carregando, recarregar, setData };
}

export function useDebounce<T>(valor: T, ms = 300): T {
  const [v, setV] = useState(valor);
  useEffect(() => { const t = setTimeout(() => setV(valor), ms); return () => clearTimeout(t); }, [valor, ms]);
  return v;
}
