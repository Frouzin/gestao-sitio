import os
import tempfile
import threading
import unittest
from datetime import date, timedelta
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

os.environ["SITIO_DB"] = os.path.join(tempfile.mkdtemp(), "teste.db")
import app  # noqa: E402


class TestSitio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.iniciar_db()
        cls.srv = app.ThreadingHTTPServer(("127.0.0.1", 0), app.App)
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def post(self, caminho, **dados):
        return urlopen(self.url + caminho, urlencode(dados).encode())

    def get(self, caminho="/"):
        return urlopen(self.url + caminho).read().decode()

    def test_fluxo_e_alertas(self):
        hoje = date.today()
        ontem = (hoje - timedelta(1)).isoformat()
        self.post("/financeiro", descricao="Venda de leite", tipo="Receita", data=hoje.isoformat(), valor="1.000,50")
        self.post("/financeiro", descricao="Ração", tipo="Despesa", data=hoje.isoformat(), valor="300")
        self.post("/estoque", item="Sal mineral", quantidade="2", minimo="5", unidade="saco")
        self.post("/tarefas", titulo="Consertar cerca", data=ontem, status="Pendente")
        self.post("/animais", identificacao="Mimosa", especie="Bovino", situacao="Ativo")
        painel = self.get()
        self.assertIn("R$ 700,50", painel)
        self.assertIn("Sal mineral: 2 saco (mín. 5)", painel)
        self.assertIn("atrasado", painel)
        self.assertIn("Bovino <b>1</b>", painel)

    def test_validacao_e_exclusao(self):
        for dados in ({"item": "X", "quantidade": "abc"}, {"item": ""}, {"item": "X", "categoria": "<script>"}):
            with self.assertRaises(HTTPError) as e:
                self.post("/estoque", **dados)
            self.assertEqual(e.exception.code, 400)
        with self.assertRaises(HTTPError) as e:
            self.get("/inexistente")
        self.assertEqual(e.exception.code, 404)
        self.post("/maquinas", equipamento="Trator <b>")
        self.assertIn("Trator &lt;b&gt;", self.get("/maquinas"))
        with app.conectar() as c:
            id_ = c.execute("SELECT id FROM maquinas").fetchone()[0]
        self.post("/maquinas/excluir", id=id_)
        self.assertIn("Nenhum registro ainda", self.get("/maquinas"))


if __name__ == "__main__":
    unittest.main()
