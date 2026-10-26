"""Persistência entre processos independentes das duas interfaces."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import textwrap
import unittest


TERMINAL_SCRIPT = """
from pathlib import Path
import sys
from bank_app.interfaces import bank_terminal
from bank_app.persistence.database import Database

# Só substitui o caminho dos dados; executa o ponto de entrada real do terminal.
database = Database(Path(sys.argv[1]))
bank_terminal.Database = lambda: database
raise SystemExit(bank_terminal.main())
"""


GUI_SCRIPT = """
from pathlib import Path
import sys
from bank_app.interfaces import bank_gui
from bank_app.persistence.database import Database

database = Database(Path(sys.argv[1]))
phase = sys.argv[2]
original_app = bank_gui.BankApp
failures = []

def create_app(bank, persistence):
    app = original_app(bank, persistence, visible=False)

    def interact():
        try:
            if phase == 'create':
                app.name_var.set('João Silva')
                app.cpf_var.set('111.111.111-11')
                app.create_holder_button.invoke()
            holder = next(bank.holders())
            app.holders_tree.selection_set(str(id(holder)))
            app.refresh_accounts()
            if phase == 'create':
                app.new_account_button.invoke()
            account = holder.get_account(1)
            expected = {'create': 0.0, 'withdraw': 100.75, 'read': 100.0}[phase]
            assert account.balance == expected, (phase, account.balance)
            app.accounts_tree.selection_set('1')
            app.accounts_tree.event_generate('<<TreeviewSelect>>')
            app.update()
            if phase == 'create':
                for value in ('100,50', '0.25'):
                    app.amount_var.set(value)
                    app.deposit_button.invoke()
            elif phase == 'withdraw':
                for value in ('0.25', '0,50'):
                    app.amount_var.set(value)
                    app.withdraw_button.invoke()
            assert not app._unsaved_changes
            app.close()
        except BaseException as error:
            failures.append(repr(error))
            app.destroy()

    def callback_error(error_type, error, traceback):
        failures.append(repr(error))
        app.destroy()

    app.report_callback_exception = callback_error
    app.after(0, interact)
    return app

def unexpected_dialog(*args, **kwargs):
    raise AssertionError(('Caixa de erro inesperada', args))

# Usa widgets, eventos e mainloop reais; só oculta a janela e troca o caminho.
bank_gui.Database = lambda: database
bank_gui.BankApp = create_app
bank_gui.messagebox.showerror = unexpected_dialog
result = bank_gui.main()
if failures:
    raise AssertionError(failures)
raise SystemExit(result)
"""


class InterfaceRestartTests(unittest.TestCase):
    def run_process(self, script, path, phase, entries=()):
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "-c", textwrap.dedent(script),
             str(path), phase],
            cwd=Path(__file__).resolve().parents[1],
            input="\n".join(entries) + "\n",
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def assert_snapshot(self, path, balance):
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), [
            {"name": "João Silva", "cpf": "111.111.111-11",
             "accounts": [{"number": 1, "balance": balance}]}
        ])

    def test_terminal_close_reopen_and_decimal_separators(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bank.json"
            self.run_process(TERMINAL_SCRIPT, path, "create", [
                "1", "João Silva", "111.111.111-11",  # Cadastra titular.
                "2", "", "1", "2",                  # Busca e cria conta.
                "1", "1",                            # Seleciona conta.
                "1", "100,50", "1", "0.25",          # Depósitos com vírgula/ponto.
                "0", "0", "0",                       # Encerra o programa.
            ])
            self.assert_snapshot(path, 100.75)
            output = self.run_process(TERMINAL_SCRIPT, path, "withdraw", [
                "2", "", "1", "1", "1",             # Reabre e seleciona conta.
                "2", "0.25", "2", "0,50",            # Saques com ponto/vírgula.
                "0", "0", "0",
            ])
            self.assertIn("100.75", output)
            self.assert_snapshot(path, 100.0)
            output = self.run_process(TERMINAL_SCRIPT, path, "read", [
                "2", "", "1", "1", "1", "0", "0", "0",
            ])
            self.assertIn("100.00", output)
            self.assert_snapshot(path, 100.0)

    def test_gui_close_reopen_and_decimal_separators(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bank.json"
            for phase, balance in (("create", 100.75), ("withdraw", 100.0), ("read", 100.0)):
                with self.subTest(phase=phase):
                    self.run_process(GUI_SCRIPT, path, phase)
                    self.assert_snapshot(path, balance)


if __name__ == "__main__":
    unittest.main()
