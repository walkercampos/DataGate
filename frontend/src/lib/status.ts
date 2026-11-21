import type { Cor } from "../components/ui";
import type { StatusAgendamento } from "./types";

export const STATUS: Record<StatusAgendamento, { rotulo: string; cor: Cor; ativo: boolean }> = {
  agendado: { rotulo: "Agendado", cor: "azul", ativo: true },
  presente: { rotulo: "Presente", cor: "verde", ativo: true },
  falta: { rotulo: "Falta", cor: "laranja", ativo: true },
  cancelado_com_credito: { rotulo: "Cancelou · crédito gerado", cor: "roxo", ativo: false },
  cancelado_sem_credito: { rotulo: "Cancelou fora do prazo", cor: "cinza", ativo: false },
  cancelado_contrato: { rotulo: "Contrato encerrado", cor: "cinza", ativo: false },
};
