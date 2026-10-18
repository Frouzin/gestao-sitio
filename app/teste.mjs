// Testa as regras do app (script id="logica" do index.html). Uso: node app/teste.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const html = readFileSync(new URL("index.html", import.meta.url), "utf8");
const codigo = html.match(/<script id="logica">([\s\S]*?)<\/script>/)[1];
const ctx = vm.createContext({});
vm.runInContext(codigo + "\nthis.api = { MODS, lerNumero, validar, resumo, relativo, somarDias };", ctx);
const { lerNumero, validar, resumo, relativo, somarDias } = ctx.api;
const j = x => JSON.parse(JSON.stringify(x));  // objetos do vm vêm de outro "realm"

assert.equal(lerNumero("1.234,56"), 1234.56);
assert.equal(lerNumero("12,5"), 12.5);
assert.equal(lerNumero("12.5"), 12.5);
assert.ok(Number.isNaN(lerNumero("abc")));

assert.match(validar("estoque", { item: "" }).erro, /Item/);
assert.match(validar("estoque", { item: "Sal", quantidade: "x" }).erro, /número/);
assert.match(validar("estoque", { item: "Sal", categoria: "<script>" }).erro, /opções/);
assert.match(validar("tarefas", { titulo: "A", data: "18/10/2026" }).erro, /data/);
assert.deepEqual(j(validar("financeiro", { descricao: "Leite", tipo: "Receita", valor: "1.000,50", data: "" }).rec),
  { descricao: "Leite", tipo: "Receita", categoria: null, data: null, valor: 1000.5 });

assert.equal(somarDias("2026-10-30", 3), "2026-11-02");
assert.equal(relativo("2026-10-18", "2026-10-18"), "hoje");
assert.equal(relativo("2026-10-21", "2026-10-18"), "em 3 dias");
assert.equal(relativo("2026-10-16", "2026-10-18"), "há 2 dias");

const h = "2026-10-18";
const dados = {
  tarefas: [{ id: "t1", titulo: "Cerca", data: "2026-10-15", status: "Pendente" }, { id: "t2", titulo: "Feita", data: "2026-10-15", status: "Feita" },
    { id: "t3", titulo: "Longe", data: "2026-12-01", status: "Pendente" }],
  animais: [{ especie: "Bovino", situacao: "Ativo" }, { especie: "Bovino" }, { especie: "Bovino", situacao: "Vendido" }],
  sanidade: [{ id: "s1", animal: "Lote 1", tipo: "Vacina", proxima: "2026-10-20" }],
  lavouras: [{ id: "l1", cultura: "Milho", situacao: "Plantada", colheita: "2026-11-10" }, { id: "l2", cultura: "Feijão", situacao: "Colhida", colheita: "2026-10-20" }],
  producao: [{ produto: "Leite", unidade: "L", quantidade: 100, data: "2026-10-01" }, { produto: "Leite", unidade: "L", quantidade: 20, data: "2026-10-02" },
    { produto: "Leite", unidade: "L", quantidade: 999, data: "2026-09-30" }],
  estoque: [{ id: "e1", item: "Ração", quantidade: 2, minimo: 5 }, { id: "e2", item: "Sal", quantidade: 9, minimo: 5, validade: "2026-11-01" }],
  maquinas: [],
  financeiro: [{ tipo: "Receita", valor: 1000, data: "2026-10-05" }, { tipo: "Despesa", valor: 300, data: "2026-10-06", categoria: "Insumos" },
    { tipo: "Despesa", valor: 50, data: "2026-05-01" }, { tipo: "Receita", valor: 70, data: "2026-04-30" }],
};
const r = resumo(dados, h);
assert.equal(r.atual.rec, 1000);
assert.equal(r.atual.desp, 300);
assert.equal(r.geral, 720);
assert.deepEqual(j(r.meses.map(m => m.mes)), ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]);
assert.equal(r.meses[0].desp, 50);  // abril fica fora da janela de 6 meses
assert.deepEqual(j(r.categorias), { Insumos: 300 });
assert.deepEqual(j(r.rebanho), { Bovino: 2 });
assert.deepEqual(j(r.producao), { "Leite|L": 120 });
assert.equal(r.pendentes, 2);
assert.equal(r.atrasadas, 1);
assert.deepEqual(j(r.alertas.map(a => a.id)), ["t1", "s1", "e2", "l1", "e1"]);  // por data, sem data no fim

console.log("ok — todas as regras passaram");
