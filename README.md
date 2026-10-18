# Gestão do Sítio

Sistema web simples para administrar um sítio. Não precisa instalar nada além do Python 3.

```bash
python3 app.py          # abre em http://localhost:8000
python3 -m unittest     # testes
```

Os dados ficam no arquivo `sitio.db` (SQLite). Para fazer backup, basta copiar esse arquivo.

## Módulos

| Módulo | Para quê |
|---|---|
| **Painel** | Resumo do mês (receitas, despesas, saldo), rebanho ativo, produção e alertas |
| **Tarefas** | O que precisa ser feito, prazo e responsável |
| **Animais** | Cadastro do rebanho: brinco/nome, espécie, sexo, nascimento, peso, lote/pasto |
| **Sanidade animal** | Vacinas, vermífugos, medicamentos, pesagens, inseminações, partos |
| **Lavouras e hortas** | Culturas por talhão/canteiro, área, plantio e colheita prevista |
| **Produção** | Leite, ovos, colheitas etc., com quantidade e destino |
| **Estoque e insumos** | Ração, adubo, sementes, remédios, combustível, com estoque mínimo e validade |
| **Máquinas** | Trator, implementos, bombas, com horímetro e manutenções |
| **Financeiro** | Receitas e despesas por categoria |

## Alertas no painel

- Tarefas pendentes atrasadas ou para os próximos 7 dias
- Vacinas/manejos com "próxima aplicação" nos próximos 7 dias (apague a data depois de aplicar)
- Estoque abaixo do mínimo e insumos vencendo em até 30 dias
- Lavouras plantadas com colheita prevista em até 30 dias
- Máquinas com manutenção nos próximos 7 dias (apague a data depois de fazer)

## Usar no celular pela rede do sítio

```bash
HOST=0.0.0.0 python3 app.py
```

Depois abra `http://IP-DO-COMPUTADOR:8000` no celular. **Atenção:** não há login; qualquer pessoa
na mesma rede consegue ver e alterar os dados. Não exponha na internet.

## Adicionar um campo ou módulo

Tudo é definido no dicionário `MODULOS` em `app.py`. Um módulo novo cria a tabela sozinho; um campo
novo em módulo existente precisa de `ALTER TABLE` no `sitio.db`.
