# Sistema Construtor de Horários Escolares (OR-Tools CP-SAT Solver)

Este projeto é uma aplicação autónoma em Python desenvolvida para resolver o complexo problema de agendamento e otimização de grades horárias institucionais. Utilizando o motor de Programação por Restrições da Google (**OR-Tools CP-SAT**), o sistema substitui abordagens tradicionais e softwares de prateleira engessados por um motor customizado altamente focado na ergonomia docente, legislação trabalhista e eficiência pedagógica.

---

## 🚀 Funcionalidades Principais

O pipeline do sistema está estruturado em uma arquitetura de 4 camadas integradas:

[Arquivo .xlsx] ──> [Automação & Parser] ──> [Heurística & Motor CP-SAT] ──> [Planilhas Coloridas]

### 1. Ingestão Automatizada e Pipeline de Dados
* **Conversor Batch Excel para CSV:** Elimina o trabalho manual de exportar abas do Excel. O script lê dinamicamente o arquivo principal `Horário 2026 (1).xlsx`, isola as abas dos cursos (`INFO`, `EDF`) e de metadados (`Docentes`), gerando automaticamente os arquivos na pasta temporária `csv_extraidos/`.
* **Tradutor de Restrições Textuais:** Transforma texto livre humano da planilha em matrizes lógicas booleanas interpretáveis pelo algoritmo.

### 2. O Motor de Otimização e Regras Escolares
O coração da aplicação foi blindado para processar regras multidimensionais complexas, divididas nas seguintes categorias estritas:

#### 🛑 Regras Institucionais e Bloqueios de Turno
* **Unicidade Absoluta:** Um professor não pode estar em duas turmas em simultâneo, e uma turma não pode ter duas disciplinas sobrepostas.
* **Mapeamento de Blocos:** O dia escolar é dividido em 15 blocos: Manhã (6 blocos), Tarde (5 blocos) e Noite (4 blocos).
* **Gestão do Diurno (Bloqueios de Tarde):**
  * Às **Terças, Quintas e Sextas-feiras**, o turno da tarde é globalmente desativado para todas as turmas do Diurno.
  * Às **Segundas-feiras**, o turno da tarde é bloqueado especificamente para as turmas `2º Ano de Edificações (EDF-2)` e `3º Ano de Informática (INFO-3)`.

#### ⚖️ Regras Laborais e Qualidade de Vida do Professor
* **Limite de Turnos Diários:** É estritamente proibido que um professor lecione nos três turnos (Manhã, Tarde e Noite) no mesmo dia. O limite é de no máximo **2 turnos ativos**.
* **Interstício Legal (Proteção ao Trabalhador):** Se um docente der aula no último horário da noite (N4), o algoritmo bloqueia automaticamente a sua presença nos dois primeiros blocos da manhã seguinte (M1 e M2).
* **Gestão Inteligente de Gaps (Dias Ociosos):** * Se o professor trabalhar 3 ou mais dias na semana, o máximo de dias ociosos permitidos no meio da sua escala é **1 dia**.
  * **Regra Estrita de 2 Dias:** Se a carga horária for compactada para exatamente 2 dias de trabalho, eles **têm de ser obrigatoriamente seguidos** (Gap = 0), proibindo escalas exaustivas espaçadas.

#### 📐 Geometria Pedagógica e Contiguidade
O motor proíbe que aulas fiquem "espalhadas" ao longo do dia, aplicando regras rígidas de acordo com a Carga Horária Semanal (CH):
* **CH = 2:** Obrigatório bloco único de 2 aulas contíguas. Proibido formato (1+1).
* **CH = 3:** Força estritamente a divisão em **(2+1)**. Permite um bloco duplo e apenas uma aula isolada em dia diferente. Proibido o formato (1+1+1).
* **CH = 4 (Noturno):** Concentração ininterrupta das 4 aulas na mesma noite.
* **CH = 4 (Diurno):** Obriga à divisão equilibrada em **(2+2)** em dias diferentes. Proibido aulas isoladas.
* **CH >= 5:** Força a organização em blocos pares. Bloqueia completamente aulas isoladas.

### 3. Inteligência Artificial: Heurísticas e Resolução Resiliente

* **Compactação Dinâmica de Dias (Pré-processador):** Limita os dias de trabalho na instituição baseando-se no volume de aulas, aplicando sub-rodízios para não esvaziar o campus num único dia:
  * **< 5 horas:** Compactado para apenas **1 dia**.
  * **5 a 8 horas:** Compactado para o máximo de **2 dias**.
  * **9 a 16 horas:** Compactado para o máximo de **3 dias** (Rodízio forçando dias de turno integral: Seg-Ter ou Qui-Sex).
  * **Acima de 16 horas:** Sem limites sintéticos (Otimizado por demanda).
* **Atração Magnética (Soft Constraint):** Disciplinas de *"Práticas Profissionais Articuladoras"* recebem um prêmio matemático (+1000 pontos) caso sejam alocadas à **Quarta-Feira** (dia de maior disponibilidade de docentes), orientando o motor a preferir este dia.
* **Estratégia de Busca de Piores Casos:** Calcula a "densidade de restrição" (Aulas / Dias Livres) de cada professor. Utiliza a estratégia `CHOOSE_FIRST` para construir a árvore de busca focando primeiro nos professores mais complexos e engessados.
* **Minimização de Janelas:** A função objetivo pune matematicamente buracos na agenda, "espremendo" as aulas para começarem mais tarde e acabarem mais cedo no mesmo dia.
* **Motor de Duas Fases e Auditor de Gargalos:** O sistema tenta resolver o Noturno primeiro (Fase 1) e depois o Diurno (Fase 2). Caso seja um modelo matematicamente insolúvel, ele gera planilhas parciais preenchendo o máximo possível e imprime um **Raio-X de Diagnóstico** indicando o exato gargalo humano (Ex: restrição severa de dias, estrangulamento da grade do docente, superlotação da turma ou falta de interseção para aulas).

### 4. Módulo de Exportação Visual Dinâmica
O resultado da matriz matemática é traduzido pela biblioteca `openpyxl` em dois arquivos Excel customizados:
* **`Horarios_Turmas_2026.xlsx`:** Grelhas separadas por abas para cada turma (Alunos/Coordenação).
* **`Horarios_Docentes_2026.xlsx`:** Grelhas individuais por aba para cada professor da instituição.
* *Diferenciais Visuais:* Cores pastéis geradas via hash algorítmico (uma disciplina/turma mantém sempre a mesma cor em toda a grade), sombreamento por turno e relatório de métricas de alocação de docentes no terminal.

---

## 📂 Estrutura do Projeto

O código-fonte é modularizado para manter a manutenibilidade e a separação de responsabilidades:

* **`main.py`:** Orquestrador central que executa o pipeline em cascata e limpa execuções antigas.
* **`automatizar_excel.py`:** Gerencia a leitura do `.xlsx` de entrada e extrai os arquivos `.csv`.
* **`parser_dados.py`:** Filtra os dados e converte textos para dicionários estruturados.
* **`motor_matematico.py`:** Onde residem o modelo OR-Tools, regras lineares, lógica heurística e função objetivo.
* **`exportador_excel.py`:** Design, estilização, geração de cores em HEX e salvamento das planilhas finais.
* **`.gitignore`:** Proteção e segurança. Impede o envio acidental de planilhas institucionais reais para o GitHub.

---

## 🛠️ Como Configurar e Executar

### 1. Clonar o Repositório e Configurar o Ambiente Virtual
No terminal do seu VS Code, execute:
```bash
# Clonar o repositório
git clone [https://github.com/jsambarreto/sistema-construtor-horario.git](https://github.com/jsambarreto/sistema-construtor-horario.git)
cd sistema-construtor-horario

# Criar o ambiente virtual (venv)
python -m venv venv

# Ativar o ambiente virtual
# No Windows:
.\venv\Scripts\activate
# No Linux/macOS:
source venv/bin/activate