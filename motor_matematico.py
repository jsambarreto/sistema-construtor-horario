from ortools.sat.python import cp_model
from parser_dados import carregar_docentes, carregar_turmas

DIAS = ['SEG', 'TER', 'QUA', 'QUI', 'SEX']
M_SLOTS = list(range(0, 6))
T_SLOTS = list(range(6, 11))
N_SLOTS = list(range(11, 15))
ALL_SLOTS = list(range(15))

def determinar_turno_turma(nome_turma):
    return 'NOTURNO' if "SUB" in nome_turma.upper() else 'DIURNO'

def obter_blocos_validos(dia_idx, turno_turma, nome_turma):
    dia = DIAS[dia_idx]
    turnos = ['MANHA', 'TARDE'] if turno_turma == 'DIURNO' else ['NOITE']
        
    if dia in ['TER', 'QUI', 'SEX'] and 'TARDE' in turnos:
        turnos.remove('TARDE')
        
    nome_upper = nome_turma.upper()
    if dia == 'SEG' and ("EDF-2" in nome_upper or "INFO-3" in nome_upper) and 'TARDE' in turnos:
        turnos.remove('TARDE')

    blocos = []
    if 'MANHA' in turnos: blocos.extend(M_SLOTS)
    if 'TARDE' in turnos: blocos.extend(T_SLOTS)
    if 'NOITE' in turnos: blocos.extend(N_SLOTS)
    return blocos

def aplicar_restricoes_sinteticas(docentes, turmas):
    """
    Em vez de forçar dias fixos de folga (o que causava gargalos no Noturno),
    limitamos a QUANTIDADE de dias trabalhados e deixamos o solver
    escolher os melhores dias, respeitando as regras de "gaps".
    """
    ch_por_docente = {doc: 0 for doc in docentes}
    for demandas in turmas.values():
        for dmd in demandas:
            doc = dmd['docente']
            if doc in ch_por_docente:
                ch_por_docente[doc] += dmd['ch_semanal']

    docentes_elegiveis = []
    for doc, info in docentes.items():
        if not info.get('impedimentos', []):
            docentes_elegiveis.append(doc)
            
    docentes_elegiveis.sort()

    print(f"\n[HEURÍSTICA] Flexibilizando a compactação de {len(docentes_elegiveis)} docentes sem restrições...")
    for doc in docentes_elegiveis:
        ch_total = ch_por_docente[doc]
        
        # Define o LIMITE MÁXIMO de dias na escola
        if 0 < ch_total < 5:
            docentes[doc]['max_dias'] = 1
            print(f" -> {doc} (CH: {ch_total}): Limite máximo de 1 dia de trabalho.")
        elif 5 <= ch_total < 9:
            docentes[doc]['max_dias'] = 2
            print(f" -> {doc} (CH: {ch_total}): Limite máximo de 2 dias de trabalho.")
        elif 9 <= ch_total <= 16:
            docentes[doc]['max_dias'] = 3
            print(f" -> {doc} (CH: {ch_total}): Limite máximo de 3 dias de trabalho.")
        else:
            docentes[doc]['max_dias'] = 5
            print(f" -> {doc} (CH: {ch_total}): Sem limite sintético (Dias mapeados por demanda)")

    return docentes

def construir_modelo(turmas_alvo, docentes, restricoes_fixas=None, modo_diagnostico=False):
    modelo = cp_model.CpModel()
    alocacoes = {}
    bonus_atracao_quarta = [] 
    
    nomes_docentes = set(d['docente'] for t in turmas_alvo.values() for d in t)
    pesos_docentes = {}
    
    for doc in nomes_docentes:
        ch_total = sum(dmd['ch_semanal'] for turma, demandas in turmas_alvo.items() for dmd in demandas if dmd['docente'] == doc)
        impedimentos = docentes.get(doc, {}).get('impedimentos', [])
        dias_livres = 5 - len([imp for imp in impedimentos if imp in DIAS])
        pesos_docentes[doc] = int((ch_total / max(1, dias_livres)) * 10)

    # 1. CRIAÇÃO DE VARIÁVEIS
    for turma, demandas in turmas_alvo.items():
        turno_turma = determinar_turno_turma(turma)
        for dmd in demandas:
            disc, doc = dmd['disciplina'], dmd['docente']
            for d_idx in range(5):
                blocos_permitidos = obter_blocos_validos(d_idx, turno_turma, turma)
                for b in blocos_permitidos:
                    imp_docente = docentes.get(doc, {}).get('impedimentos', [])
                    if DIAS[d_idx] not in imp_docente:
                        var = modelo.NewBoolVar(f"V_{turma}_{disc}_{doc}_{d_idx}_{b}")
                        alocacoes[(turma, disc, doc, d_idx, b)] = var
                        
                        if "PRATICAS" in disc.upper() and "ARTICULADORA" in disc.upper() and d_idx == 2:
                            bonus_atracao_quarta.append(var)

    if restricoes_fixas:
        for chave, valor in restricoes_fixas.items():
            if chave in alocacoes:
                modelo.Add(alocacoes[chave] == valor)

    # ESTRATÉGIA DE BUSCA (Prioridade nos piores casos)
    docentes_ordenados = sorted(nomes_docentes, key=lambda d: pesos_docentes[d], reverse=True)
    vars_prioritarias = []
    for doc_prioritario in docentes_ordenados:
        vars_do_prof = [var for (t, di, do, d, b), var in alocacoes.items() if do == doc_prioritario]
        vars_prioritarias.extend(vars_do_prof)
        
    if vars_prioritarias and not modo_diagnostico:
        modelo.AddDecisionStrategy(vars_prioritarias, cp_model.CHOOSE_FIRST, cp_model.SELECT_MAX_VALUE)

    # 2. UNICIDADE
    for d_idx in range(5):
        for b in ALL_SLOTS:
            for turma in turmas_alvo.keys():
                aulas_turma = [var for (t, _, _, d, b_aloc), var in alocacoes.items() if t == turma and d == d_idx and b_aloc == b]
                if aulas_turma: modelo.AddAtMostOne(aulas_turma)
            for doc in nomes_docentes:
                aulas_doc = [var for (_, _, do, d, b_aloc), var in alocacoes.items() if do == doc and d == d_idx and b_aloc == b]
                if aulas_doc: modelo.AddAtMostOne(aulas_doc)

    # 3. REGRAS LABORAIS E RASTREIO DE DIAS
    docente_dias_trabalhados = {doc: [] for doc in nomes_docentes}
    docente_vars_otimizacao = {}
    
    for doc in nomes_docentes:
        for d_idx in range(5):
            vars_dia = [var for (_, _, do, d, _), var in alocacoes.items() if do == doc and d == d_idx]
            
            trabalha_neste_dia = modelo.NewBoolVar(f"Trabalha_{doc}_{d_idx}")
            if vars_dia:
                modelo.AddMaxEquality(trabalha_neste_dia, vars_dia)
            else:
                modelo.Add(trabalha_neste_dia == 0)
            docente_dias_trabalhados[doc].append(trabalha_neste_dia)

            if not vars_dia: continue

            trabalha_manha = modelo.NewBoolVar(f"M_{doc}_{d_idx}")
            trabalha_tarde = modelo.NewBoolVar(f"T_{doc}_{d_idx}")
            trabalha_noite = modelo.NewBoolVar(f"N_{doc}_{d_idx}")

            aulas_m = [v for (t, di, do, d, b), v in alocacoes.items() if do == doc and d == d_idx and b in M_SLOTS]
            aulas_t = [v for (t, di, do, d, b), v in alocacoes.items() if do == doc and d == d_idx and b in T_SLOTS]
            aulas_n = [v for (t, di, do, d, b), v in alocacoes.items() if do == doc and d == d_idx and b in N_SLOTS]

            modelo.AddMaxEquality(trabalha_manha, aulas_m + [0])
            modelo.AddMaxEquality(trabalha_tarde, aulas_t + [0])
            modelo.AddMaxEquality(trabalha_noite, aulas_n + [0])
            
            modelo.Add(trabalha_manha + trabalha_tarde + trabalha_noite <= 2)

            if d_idx < 4 and not modo_diagnostico:
                n4_hoje = [v for (t, di, do, d, b), v in alocacoes.items() if do == doc and d == d_idx and b == 14]
                m1_m2_amanha = [v for (t, di, do, d, b), v in alocacoes.items() if do == doc and d == d_idx + 1 and b in [0, 1]]
                if n4_hoje and m1_m2_amanha:
                    for var_m in m1_m2_amanha:
                        modelo.AddImplication(n4_hoje[0], var_m.Not())

        # --- NOVAS REGRAS DE GAPS INTELIGENTES ---
        dias_trab = docente_dias_trabalhados[doc]
        
        if not modo_diagnostico:
            max_dias = docentes.get(doc, {}).get('max_dias', 5)
            modelo.Add(sum(dias_trab) <= max_dias)

        trabalha_algum_dia = modelo.NewBoolVar(f'trabalha_algum_{doc}')
        modelo.AddMaxEquality(trabalha_algum_dia, dias_trab)

        start_day = modelo.NewIntVar(0, 4, f'start_{doc}')
        end_day = modelo.NewIntVar(0, 4, f'end_{doc}')
        janela = modelo.NewIntVar(0, 5, f'janela_{doc}')
        total_dias = modelo.NewIntVar(0, 5, f'total_dias_{doc}')
        
        modelo.Add(total_dias == sum(dias_trab))

        for d_idx in range(5):
            modelo.Add(start_day <= d_idx).OnlyEnforceIf(dias_trab[d_idx])
            modelo.Add(end_day >= d_idx).OnlyEnforceIf(dias_trab[d_idx])

        modelo.Add(janela == end_day - start_day + 1).OnlyEnforceIf(trabalha_algum_dia)
        modelo.Add(janela == 0).OnlyEnforceIf(trabalha_algum_dia.Not())
        
        if not modo_diagnostico:
            # 1. Regra Geral: O máximo de "buracos" no meio da semana é 1 dia.
            modelo.Add(janela - total_dias <= 1).OnlyEnforceIf(trabalha_algum_dia)
            
            # 2. Regra Estrita: Se trabalhar exatos 2 dias, os dias TÊM de ser seguidos. 
            # (Ex: Proíbe trabalhar apenas Segunda e Quarta).
            b_2dias = modelo.NewBoolVar(f'b_2dias_{doc}')
            modelo.Add(total_dias == 2).OnlyEnforceIf(b_2dias)
            modelo.Add(total_dias != 2).OnlyEnforceIf(b_2dias.Not())
            modelo.Add(janela == 2).OnlyEnforceIf(b_2dias)

        # Guarda as variáveis para serem usadas na função objetivo (Fase 5)
        docente_vars_otimizacao[doc] = (janela, dias_trab)

    # 4. CARGA HORÁRIA E CONTIGUIDADE
    for turma, demandas in turmas_alvo.items():
        turno_turma = determinar_turno_turma(turma)
        for dmd in demandas:
            disc, doc, ch = dmd['disciplina'], dmd['docente'], dmd['ch_semanal']
            aulas_disc = [var for (t, di, do, _, _), var in alocacoes.items() if t == turma and di == disc and do == doc]
            
            if not aulas_disc: continue
            if modo_diagnostico: modelo.Add(sum(aulas_disc) <= ch)
            else: modelo.Add(sum(aulas_disc) == ch)

            dias_com_aula_1 = []
            for d_idx in range(5):
                V = []
                for b in ALL_SLOTS:
                    if (turma, disc, doc, d_idx, b) in alocacoes:
                        V.append(alocacoes[(turma, disc, doc, d_idx, b)])
                    else: V.append(0)
                soma_dia = sum(V)
                
                S = [] 
                for i in range(15):
                    if isinstance(V[i], int) and V[i] == 0:
                        S.append(0)
                        continue
                    s_var = modelo.NewBoolVar(f"s_{turma}_{disc}_{d_idx}_{i}")
                    S.append(s_var)
                    if i in [0, 6, 11]: modelo.Add(s_var == V[i])
                    else:
                        prev = V[i-1]
                        if isinstance(prev, int) and prev == 0:
                            modelo.Add(s_var == V[i])
                        else:
                            modelo.Add(s_var <= V[i])
                            modelo.Add(s_var <= 1 - prev)
                            modelo.Add(s_var >= V[i] - prev)
                
                has_classes = modelo.NewBoolVar(f"has_{turma}_{disc}_{d_idx}")
                modelo.Add(soma_dia > 0).OnlyEnforceIf(has_classes)
                modelo.Add(soma_dia == 0).OnlyEnforceIf(has_classes.Not())
                modelo.Add(sum(S) == has_classes)
                
                b_is_1 = modelo.NewBoolVar(f"is1_{turma}_{disc}_{d_idx}")
                modelo.Add(soma_dia == 1).OnlyEnforceIf(b_is_1)
                modelo.Add(soma_dia != 1).OnlyEnforceIf(b_is_1.Not())
                
                if ch == 2:
                    modelo.AddLinearConstraint(soma_dia, 0, 2)
                    modelo.Add(b_is_1 == 0)
                elif ch == 3:
                    modelo.AddLinearConstraint(soma_dia, 0, 3)
                    dias_com_aula_1.append(b_is_1)
                elif ch == 4:
                    if turno_turma == 'NOTURNO':
                        modelo.AddLinearConstraint(soma_dia, 0, 4)
                        modelo.Add(b_is_1 == 0)
                        modelo.Add(soma_dia != 2)
                        modelo.Add(soma_dia != 3)
                    else:
                        modelo.AddLinearConstraint(soma_dia, 0, 2)
                        modelo.Add(b_is_1 == 0)
                elif ch >= 5:
                    modelo.AddLinearConstraint(soma_dia, 0, ch)
                    modelo.Add(b_is_1 == 0)
                    modelo.Add(soma_dia != 4)
                    modelo.Add(soma_dia != 5)

            if ch == 3 and dias_com_aula_1:
                modelo.Add(sum(dias_com_aula_1) <= 1)

    # 5. OTIMIZAÇÃO
    if modo_diagnostico:
        modelo.Maximize(sum(alocacoes.values()))
    else:
        objetivos = []
        for doc in nomes_docentes:
            peso_docente = pesos_docentes[doc]
            janela, dias_trab = docente_vars_otimizacao[doc]
            
            # Penaliza janelas grandes para obrigar o solver a juntar as aulas
            objetivos.append(janela * peso_docente)
            objetivos.append(sum(dias_trab) * peso_docente)

            # Bônus para incentivar que as turmas ocorram nos dias de Integral
            max_dias_prof = docentes.get(doc, {}).get('max_dias', 5)
            if max_dias_prof <= 3:
                objetivos.append(-dias_trab[0] * 30)  # Bónus leve para Segunda-Feira
                objetivos.append(-dias_trab[2] * 30)  # Bónus leve para Quarta-Feira

        if objetivos:
            modelo.Minimize(sum(objetivos) - (sum(bonus_atracao_quarta) * 1000))
        elif bonus_atracao_quarta:
            modelo.Maximize(sum(bonus_atracao_quarta))

    return modelo, alocacoes

def executar_diagnostico(turmas_alvo, docentes, restricoes_fixas=None):
    print("\n[RAIO-X] A gerar a melhor grelha parcial possível contornando os conflitos globais...")
    modelo_diag, aloc_diag = construir_modelo(turmas_alvo, docentes, restricoes_fixas, modo_diagnostico=True)
    solver_diag = cp_model.CpSolver()
    solver_diag.parameters.max_time_in_seconds = 120.0
    status_diag = solver_diag.Solve(modelo_diag)
    
    if status_diag in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print("\n" + "="*60)
        print(" 🚨 RELATÓRIO DE CHOQUES E AUDITORIA DE GARGALOS")
        print("="*60)
        falhas = 0
        for turma, demandas in turmas_alvo.items():
            for dmd in demandas:
                disc, doc, ch = dmd['disciplina'], dmd['docente'], dmd['ch_semanal']
                vars_aula = [var for (t, di, do, _, _), var in aloc_diag.items() if t == turma and di == disc and do == doc]
                
                alocadas = int(sum(solver_diag.Value(var) for var in vars_aula))
                if alocadas < ch:
                    faltam = ch - alocadas
                    falhas += 1
                    
                    impedimentos = docentes.get(doc, {}).get('impedimentos', [])
                    dias_livres = [d for d in DIAS if d not in impedimentos]
                    
                    aulas_totais_doc = sum(solver_diag.Value(v) for (t, di, do, d, b), v in aloc_diag.items() if do == doc)
                    aulas_totais_turma = sum(solver_diag.Value(v) for (t, di, do, d, b), v in aloc_diag.items() if t == turma)
                    
                    print(f"\n❌ GARGALO: {turma} | {disc} ({doc})")
                    print(f"   📊 Status: Pediu {ch} aulas -> Alocou {alocadas} -> Faltam {faltam}")
                    print("   🔍 Diagnóstico:")
                    
                    if len(dias_livres) <= 2:
                        print(f"      - Motivo Primário: Restrição severa de dias. O professor só está autorizado a trabalhar em {dias_livres}.")
                        
                    elif aulas_totais_doc >= (len(dias_livres) * 5): 
                        print(f"      - Motivo Primário: Agenda do professor estrangulada. Ele já tem {aulas_totais_doc} aulas empacotadas in apenas {len(dias_livres)} dias livres na instituição.")
                        
                    elif aulas_totais_turma >= 35: 
                        print(f"      - Motivo Primário: Superlotação da Turma. A turma '{turma}' já está com a grade quase cheia ({aulas_totais_turma} aulas) e não possui blocos disponíveis que coincidam com o professor.")
                        
                    else:
                        if ch == 3:
                            print(f"      - Motivo Primário: Esgotamento de Interseção de Horários. O código JÁ APLICA a regra de 2+1 para turmas de 3 horas. O problema é que, após encaixar o bloco de 2 aulas, a agenda do professor '{doc}' nos dias {dias_livres} não possuía NENHUM horário vazio em comum com a turma '{turma}' para alocar a 3ª aula solta.")
                        else:
                            print(f"      - Motivo Primário: Conflito Geométrico de Blocos (Contiguidade). O professor tem dias livres {dias_livres}, mas a regra que proíbe aulas isoladas (para {ch}h) impediu o encaixe num 'buraco' de 1 aula.")
        
        if falhas > 0:
            print("\n" + "-"*60)
            print("[AÇÃO AUTOMÁTICA] Os ficheiros Excel gerados terão as células correspondentes a estes bloqueios em branco.")
        return solver_diag, status_diag, aloc_diag
    
    return None, status_diag, None

def resolver_horario_estruturado(docentes, turmas):
    print("\n" + "="*40)
    print(" MOTOR DE RESOLUÇÃO (HEURÍSTICO + OTIMIZADO)")
    print("="*40)

    docentes_otimizados = aplicar_restricoes_sinteticas(docentes, turmas)
    turmas_noturno = {k: v for k, v in turmas.items() if determinar_turno_turma(k) == 'NOTURNO'}
    
    print("\n[FASE 1] A processar turmas Noturnas (SUB)...")
    modelo_f1, aloc_f1 = construir_modelo(turmas_noturno, docentes_otimizados)
    solver_f1 = cp_model.CpSolver()
    solver_f1.parameters.max_time_in_seconds = 45.0
    status_f1 = solver_f1.Solve(modelo_f1)

    restricoes_fixas = {}
    if status_f1 in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(" -> Noturno resolvido com sucesso. Congelando horários.")
        for chave, var in aloc_f1.items():
            restricoes_fixas[chave] = solver_f1.Value(var)
    else:
        print(" -> [AVISO] O Noturno apresentou conflitos matemáticos quando isolado.")
        print(" -> A transitar sem congelamentos. A tentar resolver toda a grade escolar em simultâneo...")

    print("\n[FASE 2] A processar grade GLOBAL (Diurno + Noturno) com otimização e compactação...")
    modelo_f2, aloc_f2 = construir_modelo(turmas, docentes_otimizados, restricoes_fixas)
    solver_f2 = cp_model.CpSolver()
    solver_f2.parameters.max_time_in_seconds = 180.0 
    status_f2 = solver_f2.Solve(modelo_f2)

    if status_f2 in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f"\n[SUCESSO GLOBAL] Grelha otimizada gerada! Status: {solver_f2.StatusName()}")
        return solver_f2, status_f2, aloc_f2, DIAS
    else:
        print("\n[FALHA GLOBAL] Conflito detetado na fase Diurna. A extrair horários parciais de TODAS as turmas para Excel...")
        solver_diag, status_diag, aloc_diag = executar_diagnostico(turmas, docentes_otimizados, restricoes_fixas)
        return solver_diag, status_diag, aloc_diag, DIAS

def gerar_resumo_alocacao_professores(solver, alocacoes):
    print("\n" + "="*70)
    print(" 📋 RESUMO DE ALOCAÇÃO E PRESENÇA DOS PROFESSORES")
    print("="*70)
    print("Professor; Numero de aulas; Dias no campus; Qnt dias sem aulas")
    print("-"*70)

    dados_prof = {}
    DIAS_NOMES = ['SEG', 'TER', 'QUA', 'QUI', 'SEX']

    for (turma, disc, doc, dia_idx, bloco), var in alocacoes.items():
        if solver.Value(var) == 1:
            if doc not in dados_prof:
                dados_prof[doc] = {d: 0 for d in range(5)}
            dados_prof[doc][dia_idx] += 1

    for prof in sorted(dados_prof.keys()):
        total_aulas = sum(dados_prof[prof].values())
        dias_no_campus_lista = [DIAS_NOMES[d] for d in range(5) if dados_prof[prof][d] > 0]
        dias_no_campus_str = "-".join(dias_no_campus_lista) if dias_no_campus_lista else "NENHUM"
        qnt_dias_sem_aula = 5 - len(dias_no_campus_lista)
        
        print(f"{prof}; {total_aulas} aulas; [{dias_no_campus_str}]; {qnt_dias_sem_aula} dias livres")
    
    print("="*70 + "\n")