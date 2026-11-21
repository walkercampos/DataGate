export type Usuario = { id: string; nome: string; email: string; papel: string; tenant_id: string; estudio_nome: string };
export type AuthResp = { access_token: string; token_type: string; usuario: Usuario };

export type Estudio = {
  id: string;
  nome: string;
  capacidade_padrao_turma: number;
  antecedencia_cancelamento_horas: number;
  validade_credito_dias: number;
  fuso_horario: string;
};

export type Aluno = {
  id: string;
  nome: string;
  telefone: string;
  email: string | null;
  observacoes: string | null;
  ativo: boolean;
  creditos_reposicao: number;
  creditos_validade_ate: string | null;
  criado_em: string;
};

export type StatusAgendamento =
  | "agendado" | "cancelado_com_credito" | "cancelado_sem_credito" | "cancelado_contrato" | "presente" | "falta";

export type Participante = {
  agendamento_id: string;
  aluno_id: string;
  aluno_nome: string;
  tipo: "regular" | "reposicao";
  status: StatusAgendamento;
};

export type TipoAula = "grupo" | "individual";
export type Aula = {
  id: string;
  titulo: string;
  tipo: TipoAula;
  inicio: string;
  duracao_minutos: number;
  capacidade: number;
  ocupadas: number;
  vagas: number;
  participantes: Participante[];
};

export type Cancelamento = { credito_gerado: boolean; mensagem: string };

export type Plano = { id: string; nome: string; aulas_por_semana: number; valor_mensal: string; ativo: boolean; criado_em: string };

export type Horario = { dia_semana: number; hora: string };
export type Contrato = {
  id: string;
  aluno_id: string;
  aluno_nome: string;
  plano_id: string;
  plano_nome: string;
  aulas_por_semana: number;
  valor_mensal: string;
  data_inicio: string;
  data_fim: string | null;
  status: "ativo" | "encerrado";
  horarios: Horario[];
  criado_em: string;
};
export type Grade = { contrato_id: string; ano: number; mes: number; agendadas: number; ja_existentes: number; aulas_criadas: number; lotadas: string[] };

export type Registro = {
  id: string;
  aluno_id: string;
  agendamento_id: string | null;
  tipo: "avaliacao" | "evolucao";
  titulo: string;
  conteudo: string;
  dor_eva: number | null;
  autor_id: string;
  autor_nome: string;
  status: "rascunho" | "assinado";
  assinado_por: string | null;
  assinado_por_nome: string | null;
  assinado_em: string | null;
  hash_sha256: string | null;
  criado_em: string;
  atualizado_em: string | null;
};
export type Verificacao = { id: string; hash_registrado: string; hash_recalculado: string; integro: boolean };
