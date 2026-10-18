"""Gestão do Sítio — app web sem dependências (Python 3 + SQLite).

Uso: python3 app.py  ->  abra http://localhost:8000
"""
import html
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DB = os.environ.get("SITIO_DB", "sitio.db")

# Cada módulo vira uma tabela, uma lista e um formulário.
# Campo: (coluna, rótulo, tipo); tipo "a|b|c" vira lista de opções. O primeiro campo é obrigatório.
MODULOS = {
    "tarefas": ("Tarefas", [
        ("titulo", "Tarefa", "text"),
        ("data", "Prazo", "date"),
        ("responsavel", "Responsável", "text"),
        ("status", "Status", "Pendente|Feita")]),
    "animais": ("Animais", [
        ("identificacao", "Brinco/Nome", "text"),
        ("especie", "Espécie", "Bovino|Suíno|Caprino|Ovino|Equino|Aves|Outro"),
        ("sexo", "Sexo", "Fêmea|Macho"),
        ("nascimento", "Nascimento", "date"),
        ("peso", "Peso (kg)", "number"),
        ("lote", "Lote/Pasto", "text"),
        ("situacao", "Situação", "Ativo|Vendido|Morto"),
        ("obs", "Observações", "text")]),
    "sanidade": ("Sanidade animal", [
        ("animal", "Animal/Lote", "text"),
        ("tipo", "Manejo", "Vacina|Vermífugo|Medicamento|Pesagem|Inseminação|Parto|Outro"),
        ("data", "Data", "date"),
        ("produto", "Produto/Dose", "text"),
        ("proxima", "Próxima aplicação", "date"),
        ("obs", "Observações", "text")]),
    "lavouras": ("Lavouras e hortas", [
        ("cultura", "Cultura", "text"),
        ("talhao", "Talhão/Canteiro", "text"),
        ("area", "Área (ha)", "number"),
        ("plantio", "Plantio", "date"),
        ("colheita", "Colheita prevista", "date"),
        ("situacao", "Situação", "Planejada|Plantada|Colhida|Perdida"),
        ("obs", "Observações", "text")]),
    "producao": ("Produção", [
        ("produto", "Produto", "text"),
        ("data", "Data", "date"),
        ("quantidade", "Quantidade", "number"),
        ("unidade", "Unidade", "L|kg|dúzia|saca|caixa|un"),
        ("destino", "Destino", "Venda|Consumo|Estoque|Trato animal"),
        ("obs", "Observações", "text")]),
    "estoque": ("Estoque e insumos", [
        ("item", "Item", "text"),
        ("categoria", "Categoria", "Ração|Adubo|Semente|Defensivo|Medicamento|Combustível|Ferramenta|Outro"),
        ("quantidade", "Quantidade", "number"),
        ("unidade", "Unidade", "kg|L|saco|un|dose"),
        ("minimo", "Estoque mínimo", "number"),
        ("validade", "Validade", "date")]),
    "maquinas": ("Máquinas", [
        ("equipamento", "Equipamento", "text"),
        ("tipo", "Tipo", "Trator|Implemento|Veículo|Bomba/Irrigação|Gerador|Roçadeira|Outro"),
        ("horimetro", "Horímetro/Km", "number"),
        ("ultima", "Última manutenção", "date"),
        ("proxima", "Próxima manutenção", "date"),
        ("obs", "Observações", "text")]),
    "financeiro": ("Financeiro", [
        ("descricao", "Descrição", "text"),
        ("tipo", "Tipo", "Despesa|Receita"),
        ("categoria", "Categoria", "Vendas|Animais|Lavoura|Insumos|Mão de obra|Máquinas|Energia/Água|Impostos|Outro"),
        ("data", "Data", "date"),
        ("valor", "Valor (R$)", "number")]),
}


@contextmanager
def conectar():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        with c:
            yield c
    finally:
        c.close()


def iniciar_db():
    # shortcut: só cria tabelas novas; coluna adicionada depois a um módulo exige ALTER TABLE manual.
    with conectar() as c:
        for nome, (_, campos) in MODULOS.items():
            cols = ", ".join(f"{col} {'REAL' if tipo == 'number' else 'TEXT'}" for col, _, tipo in campos)
            c.execute(f"CREATE TABLE IF NOT EXISTS {nome} (id INTEGER PRIMARY KEY, {cols})")


def esc(v):
    return html.escape(str(v), quote=True)


def num(v):
    return "" if v is None else (int(v) if float(v).is_integer() else v)


def br(d):
    return "" if not d else "/".join(reversed(d.split("-")))


def reais(v):
    return f"R$ {v or 0:,.2f}".translate(str.maketrans(",.", ".,"))


def mostrar(v, tipo):
    if v is None:
        return ""
    if tipo == "date":
        return br(v)
    if tipo == "number":
        return str(num(v)).replace(".", ",")
    return esc(v)


def salvar(nome, dados):
    campos = MODULOS[nome][1]
    vals = []
    for col, rotulo, tipo in campos:
        v = dados.get(col, "").strip() or None
        if v and tipo == "number":
            if "," in v:  # aceita 1.234,56
                v = v.replace(".", "").replace(",", ".")
            try:
                v = float(v)
            except ValueError:
                raise ValueError(f"{rotulo}: número inválido")
        elif v and tipo == "date":
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError(f"{rotulo}: data inválida")
        elif v and "|" in tipo and v not in tipo.split("|"):
            raise ValueError(f"{rotulo}: opção inválida")
        vals.append(v)
    if vals[0] is None:
        raise ValueError(f"{campos[0][1]} é obrigatório")
    cols = [col for col, _, _ in campos]
    with conectar() as c:
        if dados.get("id"):
            sets = ", ".join(f"{col}=?" for col in cols)
            c.execute(f"UPDATE {nome} SET {sets} WHERE id=?", vals + [int(dados["id"])])
        else:
            c.execute(f"INSERT INTO {nome} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", vals)


def excluir(nome, id_):
    with conectar() as c:
        c.execute(f"DELETE FROM {nome} WHERE id=?", (int(id_),))


def campo_html(col, rotulo, tipo, valor, obrigatorio):
    req = " required" if obrigatorio else ""
    if "|" in tipo:
        opcoes = "".join(f"<option{' selected' if o == valor else ''}>{esc(o)}</option>" for o in tipo.split("|"))
        entrada = f"<select name={col}>{opcoes}</select>"
    else:
        v = num(valor) if tipo == "number" else (valor or "")
        extra = " step=any" if tipo == "number" else ""
        entrada = f"<input type={tipo} name={col} value=\"{esc(v)}\"{extra}{req}>"
    return f"<label>{esc(rotulo)}{entrada}</label>"


def pagina_modulo(nome, editar):
    titulo, campos = MODULOS[nome]
    with conectar() as c:
        atual = c.execute(f"SELECT * FROM {nome} WHERE id=?", (editar,)).fetchone() if editar else None
        linhas = c.execute(f"SELECT * FROM {nome} ORDER BY id DESC").fetchall()
    form = "".join(campo_html(col, rot, tipo, atual[col] if atual else None, i == 0)
                   for i, (col, rot, tipo) in enumerate(campos))
    oculto = f"<input type=hidden name=id value={atual['id']}>" if atual else ""
    acao = "Salvar alterações" if atual else "Adicionar"
    cancelar = f" <a href=/{nome}>Cancelar</a>" if atual else ""
    cab = "".join(f"<th>{esc(rot)}</th>" for _, rot, _ in campos)
    corpo = "".join(
        "<tr>" + "".join(f"<td>{mostrar(r[col], tipo)}</td>" for col, _, tipo in campos)
        + f"<td class=acoes><a href='/{nome}?editar={r['id']}'>Editar</a>"
        f"<form method=post action=/{nome}/excluir onsubmit=\"return confirm('Excluir este registro?')\">"
        f"<input type=hidden name=id value={r['id']}><button class=perigo>Excluir</button></form></td></tr>"
        for r in linhas) or f"<tr><td colspan={len(campos) + 1}>Nenhum registro ainda.</td></tr>"
    return (f"<form method=post action=/{nome} class=cadastro>{oculto}{form}"
            f"<div><button>{acao}</button>{cancelar}</div></form>"
            f"<div class=tabela><table><tr>{cab}<th></th></tr>{corpo}</table></div>")


def painel():
    hoje = date.today()
    h, d7, d30 = hoje.isoformat(), (hoje + timedelta(7)).isoformat(), (hoje + timedelta(30)).isoformat()
    with conectar() as c:
        def q(sql, *p):
            return c.execute(sql, p).fetchall()
        mes = {r["tipo"]: r["s"] for r in q("SELECT tipo, SUM(valor) s FROM financeiro WHERE data LIKE ? GROUP BY tipo", h[:7] + "%")}
        geral = q("SELECT SUM(CASE tipo WHEN 'Receita' THEN valor ELSE -valor END) s FROM financeiro")[0]["s"]
        rebanho = q("SELECT especie, COUNT(*) n FROM animais WHERE COALESCE(situacao, 'Ativo')='Ativo' GROUP BY especie ORDER BY n DESC")
        prod = q("SELECT produto, unidade, SUM(quantidade) s FROM producao WHERE data LIKE ? GROUP BY produto, unidade", h[:7] + "%")
        # (título, módulo, linhas com colunas t=texto e d=data)
        alertas = [
            ("Tarefas da semana", "tarefas", q(
                "SELECT titulo || COALESCE(' — ' || responsavel, '') t, data d FROM tarefas "
                "WHERE status='Pendente' AND data <= ? ORDER BY data", d7)),
            ("Manejos sanitários", "sanidade", q(
                "SELECT animal || ': ' || tipo || COALESCE(' (' || produto || ')', '') t, proxima d FROM sanidade "
                "WHERE proxima <= ? ORDER BY proxima", d7)),
            ("Estoque baixo", "estoque", q(
                "SELECT item || ': ' || printf('%g', quantidade) || ' ' || COALESCE(unidade, '') || ' (mín. ' || printf('%g', minimo) || ')' t, NULL d "
                "FROM estoque WHERE quantidade <= minimo ORDER BY item")),
            ("Insumos vencendo", "estoque", q(
                "SELECT item t, validade d FROM estoque WHERE validade <= ? ORDER BY validade", d30)),
            ("Colheitas próximas", "lavouras", q(
                "SELECT cultura || COALESCE(' — ' || talhao, '') t, colheita d FROM lavouras "
                "WHERE situacao='Plantada' AND colheita <= ? ORDER BY colheita", d30)),
            ("Manutenções", "maquinas", q(
                "SELECT equipamento t, proxima d FROM maquinas WHERE proxima <= ? ORDER BY proxima", d7)),
        ]
    rec, desp = mes.get("Receita") or 0, mes.get("Despesa") or 0
    cards = (f"<div class=card><h3>Financeiro do mês</h3><p>Receitas <b class=ok>{reais(rec)}</b></p>"
             f"<p>Despesas <b class=ruim>{reais(desp)}</b></p><p>Saldo <b>{reais(rec - desp)}</b></p>"
             f"<p class=leve>Saldo acumulado: {reais(geral)}</p></div>"
             "<div class=card><h3>Rebanho ativo</h3>"
             + ("".join(f"<p>{esc(r['especie'])} <b>{r['n']}</b></p>" for r in rebanho) or "<p class=leve>Nenhum animal.</p>")
             + "</div><div class=card><h3>Produção do mês</h3>"
             + ("".join(f"<p>{esc(r['produto'])} <b>{mostrar(r['s'], 'number')} {esc(r['unidade'] or '')}</b></p>" for r in prod)
                or "<p class=leve>Nada registrado.</p>")
             + "</div>")
    blocos = ""
    for titulo, mod, linhas in alertas:
        itens = "".join(
            f"<li>{esc(r['t'])}" + (f" <span class={'atrasado' if r['d'] < h else 'data'}>"
                                    f"{'atrasado · ' if r['d'] < h else ''}{br(r['d'])}</span>" if r["d"] else "") + "</li>"
            for r in linhas) or "<li class=leve>Nada pendente ✓</li>"
        blocos += f"<div class=card><h3><a href=/{mod}>{titulo}</a> <small>{len(linhas)}</small></h3><ul>{itens}</ul></div>"
    return f"<div class=grade>{cards}</div><h2>Alertas</h2><div class=grade>{blocos}</div>"


CSS = """
body{font-family:system-ui,sans-serif;margin:0;background:#f4f1ea;color:#2b2b2b}
header{background:#3d6b35;color:#fff;padding:12px 16px}header a{color:#fff;text-decoration:none;margin-right:14px;white-space:nowrap;line-height:2}
header b{margin-right:24px}main{padding:16px;max-width:1200px;margin:auto}
.grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.card{background:#fff;border-radius:8px;padding:12px 16px;box-shadow:0 1px 3px #0002}.card h3{margin:0 0 8px}
.card p{display:flex;justify-content:space-between;margin:4px 0}.card ul{padding-left:18px;margin:0}.card li{margin:4px 0}
.ok{color:#2e7d32}.ruim,.atrasado{color:#c62828}.leve{color:#888}.data{color:#555}small{color:#888;font-weight:normal}
.cadastro{background:#fff;padding:12px 16px;border-radius:8px;display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;align-items:end}
label{display:flex;flex-direction:column;font-size:.85em;gap:3px}input,select,button{font:inherit;padding:6px}
button{background:#3d6b35;color:#fff;border:0;border-radius:4px;cursor:pointer}button.perigo{background:#c62828;padding:2px 8px}
.tabela{overflow-x:auto;margin-top:16px}table{border-collapse:collapse;width:100%;background:#fff}
th,td{padding:6px 8px;border-bottom:1px solid #ddd;text-align:left}.acoes{display:flex;gap:8px;align-items:center}
.erro{color:#c62828}
"""


def pagina(titulo, corpo):
    nav = "".join(f"<a href=/{n}>{esc(t)}</a>" for n, (t, _) in MODULOS.items())
    return (f"<!doctype html><html lang=pt-BR><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'><title>{esc(titulo)} · Sítio</title>"
            f"<style>{CSS}</style></head><body><header><b>🌱 Gestão do Sítio</b><a href=/>Painel</a>{nav}</header>"
            f"<main><h1>{esc(titulo)}</h1>{corpo}</main></body></html>")


class App(BaseHTTPRequestHandler):
    def enviar(self, corpo, status=200):
        dados = corpo.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def nao_encontrado(self):
        self.enviar(pagina("Não encontrado", "<p>Página não encontrada. <a href=/>Voltar ao painel</a></p>"), 404)

    def do_GET(self):
        u = urlparse(self.path)
        nome = u.path.strip("/")
        if nome == "":
            return self.enviar(pagina("Painel", painel()))
        if nome not in MODULOS:
            return self.nao_encontrado()
        editar = parse_qs(u.query).get("editar", [None])[0]
        self.enviar(pagina(MODULOS[nome][0], pagina_modulo(nome, editar)))

    def do_POST(self):
        nome, _, acao = urlparse(self.path).path.strip("/").partition("/")
        if nome not in MODULOS or acao not in ("", "excluir"):
            return self.nao_encontrado()
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho > 100_000:
            return self.enviar(pagina("Erro", "<p class=erro>Envio grande demais.</p>"), 413)
        dados = {k: v[0] for k, v in parse_qs(self.rfile.read(tamanho).decode(), keep_blank_values=True).items()}
        try:
            excluir(nome, dados.get("id")) if acao else salvar(nome, dados)
        except (ValueError, TypeError) as e:
            return self.enviar(pagina("Erro", f"<p class=erro>{esc(e)}</p><a href=/{nome}>Voltar</a>"), 400)
        self.send_response(303)
        self.send_header("Location", f"/{nome}")
        self.end_headers()


if __name__ == "__main__":
    iniciar_db()
    host, porta = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", 8000))
    print(f"Gestão do Sítio rodando em http://{host}:{porta}")
    ThreadingHTTPServer((host, porta), App).serve_forever()
