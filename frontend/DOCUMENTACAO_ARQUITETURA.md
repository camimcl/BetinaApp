# 📖 Documentação de Arquitetura: Projeto Betina Frontend

Esta documentação visa mapear toda a engenharia, lógica e arquitetura estabelecidas até o presente momento no projeto **Betina Frontend**, em preparação para as futuras integrações de Backend e aperfeiçoamentos visuais.

---

## 🏗 Integração e Stack Tecnológica (MVP)
A plataforma foi rigorosamente desenhada sobre as diretrizes acordadas pelo time de desenvolvimento para garantir altíssima performance visual, sem o peso de frameworks de UI tradicionais.

| Tecnologia | Função no Projeto |
| ---------- | ----------------- |
| **React 19** | Motor core para componentização funcional lógica e hooks nativos. |
| **Vite** | Empacotador (Bundler) ultrarrápido gerenciando os servidores locais e o build final simulado. |
| **Tailwind CSS** | Única folha de estilo da aplicação. Assegura a consistência do design pelo uso restrito de suas `utility classes` configuradas para Dark Mode + Yellow Brand. |
| **React Router v7** | Provedor de lógica Singleton (Single Page Application). Responsável pelo "Roteamento Rápido" (sem carregamento do navegador) ligando abas independentes. |
| **Framer Motion** | Substituto oficial de transições CSS. Implementado fortemente para gerar o "Feeling de App Nativo Mobile" (como a troca da tela de Chat para as estatísticas). |
| **Recharts / D3** | Renderização analítica vetorial. Responsável pelas exibições matemáticas modulares na visão de Desempenhos. |
| **Lucide React** | Padronização global de Iconografias vetoriais minimizadas (*tree-shaking* otimizado). |

---

## 🗂 Arquitetura de Pastas e Componentização
O design pattern atual prioriza o isolamento de instâncias, focando no princípio D.R.Y (Don't Repeat Yourself).

```text
src/
├── components/          --> (Pequenos blocos e módulos construtores)
│   ├── charts/          --> Gráficos Recharts (Bar/Area) altamente reutilizáveis.
│   ├── AuthCard.jsx     --> Wrapper genérico que estrutura visualmente formulários.
│   ├── Navbar.jsx       --> Cabeçalho fixo (Sticky) da aplicação autenticada.
│   └── FloatingSupport.jsx -> Extensão interativa do "Avatar de IA com Balão" persistente.
│
├── layouts/             --> (Molduras que agrupam componentes e filhos lógicos)
│   ├── AuthLayout.jsx   --> Tela escura preta e limpa (Feita para `/login` e `/cadastro`).
│   └── MainLayout.jsx   --> Moldura Padrão injetando a `<Navbar>` no topo em todas as páginas do app.
│
├── pages/               --> (Os contêineres colossais montados com os blocos)
│   ├── Cadastro.jsx & Login.jsx
│   ├── Home.jsx         --> Landing Page principal do funil (Herdando Call to actions e herotexts).
│   ├── Jogos.jsx        --> A vitrine massiva de apostas com Card Arrays mapeáveis.
│   ├── Pagamentos.jsx   --> Gateway PIX simulado com CSS Grid encriptado visualmente.
│   ├── Planos.jsx       --> Comparativo de "Tiers" (Básico/Vip) e features.
│   ├── Perfil.jsx       --> Visão central do Usuário logado contendo setinhas de opções fluidas.
│   ├── AssistenteVirtual.jsx --> Componente de Tensão: Mantém Estados lógicos (`activeView`) reativos alternando Dashboard/Chat.
│   └── ...
│
└── router/
    └── index.jsx        --> Coração da Aplicação: A matriz que acopla Páginas, Rotas e Layouts (Browser Router API).
```

---

## 🧠 Funcionamento do Core System & Interatividade

As pontes de navegação entre as telas seguem o **Fluxo Circular Sem Reload**:

1. **A Identidade do Usuário (Rotas Abertas x Fechadas):** 
   O sistema divide o App entre *Páginas Brutas* (Roteadas pelo AuthLayout, sem a barra superior para focar na conversão) e *Páginas Protegidas* (englobadas no MainLayout dispondo navegação).

2. **A "Mágica do State" (AssistenteVirtual.jsx):**
   O Workflow do assistente foi o mais arquiteturalmente demandante: a tela foi projetada contendo uma Base Lateral (`Sidebar`) que envia propriedades (`props`) para o Layout Master. Ao clicar no Sidebar, a página troca instantaneamente o componente do `[Chat IA]` para o `[Dashboard Recharts]` sem jamais piscar a tela, emulando um tablet. 

3. **Interligações Puras (`useNavigate`):**
   Todo o ecossistema é conectado e validado através do `useNavigate()` e `<Link>`. Clicou no esporte em `Jogos`? O Hook aponta direto para `/pagamentos`, e isso constrói a ilusão perfeita de processamento web em menos de 10 milissegundos.

## ⚠️ Known Issues Resolvidas
- **O Warning de Responsividade Recharts (Height -1):** Durante builds rígidos em transições React (ex: Renderizando novos componentes a partir do vácuo visual via Framer Motion), o `ResponsiveContainer` avisava que o CSS Grid demorava a calcular sua limitação estrutural. Resolvido forçando limites `minWidth={0} minHeight={0}` dentro das subpastas das views de performance.

---

> **Status e Conclusão MVP:** O Front-end estrutural está concluído e totalmente simulado de forma hermética. Aguardando próximos escopos de Otimizações Visuais High-End ou Refatorações Estruturais de Lógica de Requisições APIs.
