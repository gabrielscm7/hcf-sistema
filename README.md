# HCF — Sistema de Controle de Condicionamento Físico · Handebol

## Stack
- **Backend**: Python + FastAPI + SQLAlchemy + SQLite
- **Frontend**: HTML + CSS + JavaScript puro (sem frameworks)
- **Auth**: JWT com roles (staff / athlete)
- **Deploy**: Railway / Render / VPS

---

## Estrutura do Projeto

```
handball_app/
├── backend/
│   ├── main.py               # Entry point FastAPI + seed de dados
│   ├── database.py           # Models SQLAlchemy + get_db
│   ├── routes/
│   │   └── api.py            # Todos os endpoints REST
│   └── services/
│       ├── auth.py           # JWT + hashing
│       └── analytics.py      # ACWR, monotonia, trend, breakdown
├── frontend/
│   ├── athlete/
│   │   └── index.html        # Portal do Atleta (mobile-first)
│   └── staff/
│       └── index.html        # Painel Técnico (desktop)
├── requirements.txt
└── README.md
```

---

## Instalação Local

```bash
# 1. Clonar / entrar na pasta
cd handball_app

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Rodar o servidor
cd backend
python main.py
```

Acesse:
- **API Docs**: http://localhost:8000/docs
- **Portal Atleta**: abrir `frontend/athlete/index.html` no browser
- **Painel Técnico**: abrir `frontend/staff/index.html` no browser

---

## Credenciais de Demo

| Usuário | Senha | Perfil |
|---------|-------|--------|
| `gabriel` | `admin123` | Staff (acesso total) |
| `lucas` | `atleta123` | Atleta |
| `thiago` | `atleta123` | Atleta |
| `rafael` | `atleta123` | Atleta |
| *(demais pelo primeiro nome)* | `atleta123` | Atleta |

---

## Endpoints Principais

### Auth
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/token` | Login — retorna JWT |
| POST | `/api/auth/register` | Cadastrar usuário (staff only) |

### Atletas
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/athletes` | Listar elenco |
| POST | `/api/athletes` | Cadastrar atleta |
| GET | `/api/athletes/{id}` | Perfil do atleta |
| PUT | `/api/athletes/{id}` | Atualizar atleta |

### Carga
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/athletes/{id}/loads` | Registrar sessão |
| GET | `/api/athletes/{id}/loads` | Listar sessões |
| DELETE | `/api/athletes/{id}/loads/{load_id}` | Deletar sessão |

### Carga Externa
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/athletes/{id}/strength` | Lançar série de força |
| GET | `/api/athletes/{id}/strength` | Histórico de força |
| POST | `/api/athletes/{id}/running` | Lançar sessão de corrida |
| GET | `/api/athletes/{id}/running` | Histórico de corrida |

### Wellness
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/athletes/{id}/wellness` | Registrar wellness |
| GET | `/api/athletes/{id}/wellness` | Histórico de wellness |

### Testes
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/athletes/{id}/tests` | Lançar resultado |
| GET | `/api/athletes/{id}/tests` | Histórico de testes |

### Analytics
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/athletes/{id}/analytics/acwr` | ACWR + zona de risco |
| GET | `/api/athletes/{id}/analytics/monotony` | Monotonia + Strain |
| GET | `/api/athletes/{id}/analytics/load-breakdown` | Carga por tipo |
| GET | `/api/athletes/{id}/analytics/trend` | Tendência semanal |
| GET | `/api/group/analytics/availability` | Disponibilidade do grupo |
| GET | `/api/group/analytics/load-summary` | Resumo de carga do grupo |

---

## Deploy — Railway (recomendado)

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Criar projeto
railway init

# Deploy
railway up
```

Adicionar variável de ambiente:
```
SECRET_KEY=sua-chave-secreta-forte-aqui
```

---

## Próximas Implementações (Fase 2)

- [ ] Exportação de relatório PDF por atleta
- [ ] Exportação Excel do grupo
- [ ] Notificações push (atleta com ACWR em risco)
- [ ] Upload de foto do atleta
- [ ] Registro de lesões com timeline
- [ ] Periodização integrada ao app (microciclo visual)
- [ ] Gráficos interativos (Chart.js)
- [ ] PWA — instalável no celular como app nativo
- [ ] Modo offline com sync posterior

---

## Segurança

- Senhas com bcrypt (hash seguro)
- JWT com expiração de 12h
- Atleta só acessa os próprios dados
- Staff acessa todos os dados
- CORS configurado (ajustar origins em produção)

**Em produção, alterar `SECRET_KEY` no `auth.py` para uma chave forte e única.**
