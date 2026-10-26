"""Fluxos do terminal com entrada simulada e persistência temporária."""

import importlib.util
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from bank_app.domain.bank import Bank
from bank_app.persistence.database import Database


class TerminalTests(unittest.TestCase):
    def setUp(self):
        if importlib.util.find_spec("bank_app.interfaces") is None:
            self.fail("Pacote de interfaces ainda não implementado")
        from bank_app.interfaces.bank_terminal import BankTerminal
        self.bank = Bank()
        self.database = Mock(spec=Database)
        self.terminal = BankTerminal(self.bank, self.database)
        self.output = StringIO()
        self.capture = patch("sys.stdout", self.output)
        self.capture.start()
        self.addCleanup(self.capture.stop)

    def test_dependencies_are_injected(self):
        self.assertIs(self.terminal.bank, self.bank)
        self.assertIs(self.terminal.database, self.database)
        self.database.load.assert_not_called()

    def test_choose_returns_original_item(self):
        item = object()
        with patch("builtins.input", return_value="1"):
            self.assertIs(self.terminal.choose([item]), item)

    def test_choose_invalid_or_cancelled(self):
        for value in ("", "texto", "0", "-1", "2", "1.5"):
            with self.subTest(value=value), patch("builtins.input", return_value=value):
                self.assertIsNone(self.terminal.choose(["item"]))

    def test_choose_empty_does_not_prompt(self):
        with patch("builtins.input") as prompt:
            self.assertIsNone(self.terminal.choose([]))
        prompt.assert_not_called()

    def test_create_holder_saves(self):
        with patch("builtins.input", side_effect=["Ana", "111"]):
            self.terminal.create_holder_screen()
        self.assertEqual(next(self.bank.holders()).name, "Ana")
        self.database.save.assert_called_once_with(self.bank)

    def test_duplicate_holder_does_not_save(self):
        self.bank.create_holder("Ana", "111")
        with patch("builtins.input", side_effect=["Bia", "111"]):
            self.terminal.create_holder_screen()
        self.database.save.assert_not_called()
        self.assertIn("CPF", self.output.getvalue())

    def test_empty_holder_fields_do_not_save(self):
        with patch("builtins.input", side_effect=["", "111"]):
            self.terminal.create_holder_screen()
        self.database.save.assert_not_called()
        self.assertEqual(list(self.bank.holders()), [])

    def test_search_by_name_and_enter_list_all(self):
        holder = self.bank.create_holder("Ana Silva", "111")
        for text in ("sILVa", ""):
            with patch("builtins.input", side_effect=[text, "1"]), \
                    patch.object(self.terminal, "holder_menu") as menu:
                self.terminal.search_holder_screen()
            menu.assert_called_once_with(holder)
        self.database.save.assert_not_called()

    def test_holder_creates_account(self):
        holder = self.bank.create_holder("Ana", "111")
        with patch("builtins.input", side_effect=["2", "0"]):
            self.terminal.holder_menu(holder)
        self.assertEqual(holder.get_account(1).balance, 0)
        self.database.save.assert_called_once_with(self.bank)

    def test_list_accounts_opens_selected_account(self):
        holder = self.bank.create_holder("Ana", "111")
        self.bank.create_account(holder)
        with patch("builtins.input", return_value="1"), \
                patch.object(self.terminal, "account_menu") as menu:
            self.terminal.list_accounts_screen(holder)
        menu.assert_called_once_with(holder.get_account(1))
        self.database.save.assert_not_called()

    def test_delete_account_saves(self):
        holder = self.bank.create_holder("Ana", "111")
        self.bank.create_account(holder)
        with patch("builtins.input", return_value="1"):
            self.terminal.delete_account_screen(holder)
        self.assertEqual(list(holder.accounts()), [])
        self.database.save.assert_called_once_with(self.bank)

    def test_bad_account_number_and_missing_account_do_not_save(self):
        holder = self.bank.create_holder("Ana", "111")
        for text in ("abc", "99"):
            with patch("builtins.input", return_value=text):
                self.terminal.delete_account_screen(holder)
        self.database.save.assert_not_called()
        self.assertIn("Digite um valor numérico", self.output.getvalue())
        self.assertIn("não possui", self.output.getvalue())

    def test_comma_and_point_transactions(self):
        holder = self.bank.create_holder("Ana", "111")
        self.bank.create_account(holder)
        account = holder.get_account(1)
        with patch("builtins.input", side_effect=["1", "10,50", "2", "0.50", "0"]):
            self.terminal.account_menu(account)
        self.assertEqual(account.balance, 10)
        self.assertEqual(self.database.save.call_count, 2)

    def test_invalid_transactions_do_not_save(self):
        holder = self.bank.create_holder("Ana", "111")
        self.bank.create_account(holder)
        account = holder.get_account(1)
        for value in ("abc", "0", "-1", "nan", "inf"):
            with patch("builtins.input", return_value=value):
                self.terminal.transaction_screen(account.deposit, "Depósito")
        with patch("builtins.input", return_value="100"):
            self.terminal.transaction_screen(account.withdraw, "Saque")
        self.assertEqual(account.balance, 0)
        self.database.save.assert_not_called()
        self.assertIn("Digite um valor numérico", self.output.getvalue())
        self.assertIn("Saldo insuficiente", self.output.getvalue())

    def test_save_failure_is_visible_and_can_be_retried(self):
        self.database.save.side_effect = [PermissionError("sem acesso"), None]
        with patch("builtins.input", side_effect=["1", "Ana", "111", "3", "0"]):
            self.terminal.run()
        self.assertEqual(self.database.save.call_count, 2)
        self.assertIn("não foi salva", self.output.getvalue())
        self.assertEqual(len(list(self.bank.holders())), 1)

    def test_eof_and_keyboard_interrupt_end_cleanly(self):
        for error in (EOFError, KeyboardInterrupt):
            with patch("builtins.input", side_effect=error):
                self.terminal.run()
        self.database.save.assert_not_called()

    def test_complete_flow_with_real_json_and_reload(self):
        from bank_app.interfaces.bank_terminal import BankTerminal
        with TemporaryDirectory() as directory:
            database = Database(Path(directory) / "bank.json")
            terminal = BankTerminal(Bank(), database)
            entries = [
                "1", "João", "111",  # Cadastro.
                "2", "", "1",        # Busca e seleção do titular.
                "2",                  # Criação de conta.
                "1", "1",             # Lista e seleção da conta.
                "1", "0,30",          # Depósito.
                "2", "0.10",          # Saque.
                "0", "0", "0",        # Volta e encerra.
            ]
            with patch("builtins.input", side_effect=entries):
                terminal.run()
            loaded = database.load()
            holder = next(loaded.holders())
            self.assertEqual((holder.name, holder.cpf), ("João", "111"))
            self.assertEqual(holder.get_account(1).balance, 0.20)


if __name__ == "__main__":
    unittest.main()
