# Studio Pilates — Interface web

React + Vite + TypeScript + Tailwind. Sem banco próprio: tudo vem da API (`/api`).

- **Docker:** sobe junto com o backend (`cd ../backend && docker compose up -d --build`) em http://localhost:8080.
  O nginx serve o app e repassa `/api/*` para a API, no mesmo domínio e sem CORS.
- **Desenvolvimento:** com a API rodando em `localhost:8000`:
  ```bash
  npm install
  npm run dev        # http://localhost:5173 (proxy /api -> localhost:8000)
  ```

Telas:
- **Agenda:** semana, nova aula avulsa ou grade recorrente, detalhe da aula com presença, falta, cancelamento e reposição.
- **Alunos:** ficha com plano e horários fixos, prontuário (assinar e verificar o hash) e observações.
- **Planos.**
- **Configurações:** regras do estúdio e a geração da grade mensal.

Datas e horas são exibidas e digitadas no fuso do estúdio.
