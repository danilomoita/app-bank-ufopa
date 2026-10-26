"""Verificações repetíveis das etapas 1 a 4, sem interface e sem dados reais."""

import ast
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from bank_app.domain.account import Account
from bank_app.domain.bank import Bank
from bank_app.domain.holder import Holder
from bank_app.domain import exceptions as errors
from bank_app.persistence.database import Database, DEFAULT_PATH


class AccountTests(unittest.TestCase):
    def test_initial_state_and_format(self):
        account = Account(7)
        self.assertEqual((account.number, account.balance, str(account)), (7, 0.0, "0007"))
        self.assertEqual(str(Account(12345)), "12345")

    def test_read_only_properties(self):
        account = Account(1)
        for field in ("number", "balance"):
            with self.subTest(field=field), self.assertRaises(AttributeError):
                setattr(account, field, 10)

    def test_invalid_numbers(self):
        for value in (0, -1, True, 1.5, "1", None):
            with self.subTest(value=value), self.assertRaises(errors.InvalidDataError):
                Account(value)

    def test_invalid_initial_balances(self):
        for value in (-1, float("nan"), float("inf"), True, "10", None, 10**400):
            with self.subTest(value=value), self.assertRaises(errors.InvalidDataError):
                Account(1, value)

    def test_deposit_and_withdraw(self):
        account = Account(1, 50)
        account.deposit(25)
        account.withdraw(20)
        self.assertEqual(account.balance, 55)

    def test_invalid_transactions_preserve_balance(self):
        account = Account(1, 50)
        for operation in (account.deposit, account.withdraw):
            for value in (0, -1, float("nan"), float("inf"), True, "1", None, 10**400):
                with self.subTest(operation=operation.__name__, value=value):
                    with self.assertRaises(errors.InvalidAmountError):
                        operation(value)
                    self.assertEqual(account.balance, 50)

    def test_insufficient_funds_preserves_balance(self):
        account = Account(1, 10)
        with self.assertRaises(errors.InsufficientFundsError):
            account.withdraw(11)
        self.assertEqual(account.balance, 10)

    def test_withdraw_all(self):
        account = Account(1, 10)
        account.withdraw(10)
        self.assertEqual(account.balance, 0)

    def test_overflow_preserves_balance(self):
        account = Account(1, 1e308)
        with self.assertRaises(errors.InvalidAmountError):
            account.deposit(1e308)
        self.assertEqual(account.balance, 1e308)

    def test_decimal_withdrawals_should_allow_exact_total(self):
        # Regressão: 30 centavos devem permitir sacar 10 e depois 20 centavos.
        account = Account(1, 0.30)
        account.withdraw(0.10)
        account.withdraw(0.20)
        self.assertEqual(account.balance, 0.0)

    def test_decimal_deposits_and_insufficient_funds(self):
        account = Account(1)
        for _ in range(10):
            account.deposit(0.10)
        self.assertEqual(account.balance, 1.0)
        with self.assertRaises(errors.InsufficientFundsError):
            account.withdraw(1.01)
        self.assertEqual(account.balance, 1.0)
        account.withdraw(1.0)
        self.assertEqual(account.balance, 0.0)

    def test_small_deposit_survives_large_withdrawal(self):
        account = Account(1, 1e100)
        account.deposit(0.01)
        account.withdraw(1e100)
        self.assertEqual(account.balance, 0.01)


class HolderTests(unittest.TestCase):
    def test_creation_and_setters(self):
        holder = Holder(" Maria ", " 111 ")
        self.assertEqual((holder.name, holder.cpf), ("Maria", "111"))
        holder.name, holder.cpf = "Ana", "222"
        self.assertEqual((holder.name, holder.cpf), ("Ana", "222"))
        self.assertEqual(list(holder.accounts()), [])

    def test_invalid_fields_at_creation_and_assignment(self):
        for field in ("name", "cpf"):
            for value in ("", "   ", "\t\n", None, 123):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(errors.InvalidDataError):
                        Holder(value if field == "name" else "Ana",
                               value if field == "cpf" else "111")
                    holder = Holder("Ana", "111")
                    previous = getattr(holder, field)
                    with self.assertRaises(errors.InvalidDataError):
                        setattr(holder, field, value)
                    self.assertEqual(getattr(holder, field), previous)

    def test_add_get_delete_and_generator(self):
        holder = Holder("Ana", "111")
        account = Account(7)
        holder.add_account(account)
        self.assertIs(holder.get_account(7), account)
        self.assertTrue(inspect.isgenerator(holder.accounts()))
        self.assertEqual(list(holder.accounts()), [account])
        holder.delete_account(7)
        self.assertEqual(list(holder.accounts()), [])

    def test_duplicate_does_not_replace_account(self):
        holder = Holder("Ana", "111")
        original = Account(1, 20)
        holder.add_account(original)
        with self.assertRaises(errors.DuplicateAccountError):
            holder.add_account(Account(1, 100))
        self.assertIs(holder.get_account(1), original)

    def test_missing_accounts(self):
        holder = Holder("Ana", "111")
        for operation in (holder.get_account, holder.delete_account):
            with self.assertRaises(errors.AccountNotFoundError):
                operation(99)

    def test_separate_collections_and_no_reverse_relationship(self):
        holder, other = Holder("Ana", "111"), Holder("Bia", "222")
        account = Account(1)
        holder.add_account(account)
        self.assertEqual(list(other.accounts()), [])
        self.assertFalse(hasattr(account, "holder"))


class BankTests(unittest.TestCase):
    def setUp(self):
        self.bank = Bank()
        self.ana = self.bank.create_holder("Ana Silva", "111")
        self.bia = self.bank.create_holder("Bia Silva", "222")

    def test_duplicate_cpf_preserves_registry(self):
        with self.assertRaises(errors.DuplicateHolderError):
            self.bank.create_holder("Outra Ana", " 111 ")
        self.assertEqual(list(self.bank.holders()), [self.ana, self.bia])

    def test_generators_and_search(self):
        self.assertTrue(inspect.isgenerator(self.bank.holders()))
        self.assertTrue(inspect.isgenerator(self.bank.filter_by_name("")))
        self.assertEqual(list(self.bank.filter_by_name("sILVa")), [self.ana, self.bia])
        self.assertEqual(list(self.bank.filter_by_name("ANA")), [self.ana])
        self.assertEqual(list(self.bank.filter_by_name("")), [self.ana, self.bia])
        self.assertEqual(list(self.bank.filter_by_name("ausente")), [])

    def test_numbering_and_requested_return_type(self):
        self.assertIs(self.bank.create_account(self.ana), self.ana)
        self.bank.create_account(self.bia)
        self.assertEqual(self.ana.get_account(1).balance, 0)
        self.assertEqual(self.bia.get_account(2).balance, 0)
        self.bank.add_account(self.ana, Account(20, 100))
        self.bank.create_account(self.bia)
        self.assertEqual(self.bia.get_account(21).balance, 0)

    def test_global_duplicate_number(self):
        self.bank.add_account(self.ana, Account(10))
        for holder in (self.ana, self.bia):
            with self.assertRaises(errors.DuplicateAccountError):
                self.bank.add_account(holder, Account(10))
        self.assertEqual(list(self.bia.accounts()), [])

    def test_foreign_holder_rejected_even_with_same_fields(self):
        outsider = Holder("Ana Silva", "111")
        with self.assertRaises(errors.HolderNotFoundError):
            self.bank.add_account(outsider, Account(1))
        with self.assertRaises(errors.HolderNotFoundError):
            self.bank.create_account(outsider)
        self.assertEqual(list(outsider.accounts()), [])

    def test_numbering_after_deletions(self):
        self.bank.add_account(self.ana, Account(8))
        self.ana.delete_account(8)
        self.bank.create_account(self.bia)
        self.assertEqual(self.bia.get_account(1).balance, 0)

    def test_cpf_change_should_not_duplicate_registered_holder(self):
        # Regressão: um setter público também deve preservar a unicidade global.
        with self.assertRaises(errors.DuplicateHolderError):
            self.bia.cpf = self.ana.cpf
        self.assertEqual(self.bia.cpf, "222")

    def test_valid_cpf_changes_update_duplicate_checks(self):
        self.bia.cpf = " 333 "
        self.bia.cpf = "333"  # Manter o próprio CPF é permitido.
        with self.assertRaises(errors.DuplicateHolderError):
            self.bank.create_holder("Outra Bia", "333")
        holder = self.bank.create_holder("Clara", "222")
        self.assertEqual(holder.cpf, "222")
        with self.assertRaises(errors.DuplicateHolderError):
            holder.cpf = " 111 "
        self.assertEqual(holder.cpf, "222")

    def test_cpf_validation_is_scoped_to_each_bank(self):
        other = Bank()
        holder = other.create_holder("Clara", "111")
        holder.cpf = "222"
        self.assertEqual(holder.cpf, "222")


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "bank.json"
        self.database = Database(self.path)

    def write_data(self, data):
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_missing_file_and_default_path(self):
        self.assertEqual(list(self.database.load().holders()), [])
        self.assertFalse(self.path.exists())
        self.assertEqual(Database().path, DEFAULT_PATH)
        self.assertEqual(DEFAULT_PATH.name, "bank.json")

    def test_complete_round_trip_and_continued_operations(self):
        bank = Bank()
        holder = bank.create_holder("João Conceição", "111")
        bank.add_account(holder, Account(7, 350.5))
        bank.create_holder("Ana", "222")
        self.database.save(bank)
        raw = self.path.read_text(encoding="utf-8")
        self.assertIn("João Conceição", raw)
        self.assertIn('\n  {', raw)
        loaded = self.database.load()
        holders = list(loaded.holders())
        self.assertEqual([(h.name, h.cpf) for h in holders],
                         [("João Conceição", "111"), ("Ana", "222")])
        self.assertIsNot(holders[0], holder)
        account = holders[0].get_account(7)
        self.assertEqual(account.balance, 350.5)
        account.withdraw(50)
        loaded.create_account(holders[1])
        self.assertEqual(holders[1].get_account(8).balance, 0)
        self.database.save(loaded)
        self.assertEqual(next(self.database.load().holders()).get_account(7).balance, 300.5)

    def test_loaded_duplicate_cpf(self):
        self.write_data([{"name": "A", "cpf": "1", "accounts": []},
                         {"name": "B", "cpf": "1", "accounts": []}])
        with self.assertRaises(errors.DuplicateHolderError):
            self.database.load()

    def test_loaded_duplicate_numbers(self):
        account = {"number": 1, "balance": 0}
        for same_holder in (True, False):
            with self.subTest(same_holder=same_holder):
                data = [{"name": "A", "cpf": "1", "accounts": [account]}]
                if same_holder:
                    data[0]["accounts"].append(account)
                else:
                    data.append({"name": "B", "cpf": "2", "accounts": [account]})
                self.write_data(data)
                with self.assertRaises(errors.DuplicateAccountError):
                    self.database.load()

    def test_loaded_invalid_domain_data(self):
        for number, balance in ((0, 0), (1, -1), (True, 0), (1, float("nan"))):
            with self.subTest(number=number, balance=balance):
                self.write_data([{"name": "A", "cpf": "1", "accounts": [
                    {"number": number, "balance": balance}]}])
                with self.assertRaises(errors.InvalidDataError):
                    self.database.load()

    def test_malformed_json_does_not_become_empty_bank(self):
        self.path.write_text("{invalido", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            self.database.load()

    def test_save_replaces_previous_data(self):
        self.write_data([{"name": "A", "cpf": "1", "accounts": []}])
        self.database.save(Bank())
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), [])

    def test_load_uses_public_bank_methods(self):
        self.write_data([{"name": "A", "cpf": "1", "accounts": [
            {"number": 7, "balance": 10}]}])
        calls = []

        class TrackingBank(Bank):
            def create_holder(self, name, cpf):
                calls.append("create_holder")
                return super().create_holder(name, cpf)

            def add_account(self, holder, account):
                calls.append("add_account")
                return super().add_account(holder, account)

        with patch("bank_app.persistence.database.Bank", TrackingBank):
            self.database.load()
        self.assertEqual(calls, ["create_holder", "add_account"])

    def test_loaded_holders_keep_cpf_validation_and_decimal_operations(self):
        self.write_data([
            {"name": "A", "cpf": "1", "accounts": [{"number": 1, "balance": 0.30}]},
            {"name": "B", "cpf": "2", "accounts": []},
        ])
        bank = self.database.load()
        first, second = list(bank.holders())
        with self.assertRaises(errors.DuplicateHolderError):
            second.cpf = "1"
        account = first.get_account(1)
        account.withdraw(0.10)
        self.database.save(bank)
        reloaded = self.database.load()
        account = next(reloaded.holders()).get_account(1)
        account.withdraw(0.20)
        self.assertEqual(account.balance, 0.0)


class ArchitectureTests(unittest.TestCase):
    def test_exception_hierarchy(self):
        self.assertTrue(issubclass(errors.BankError, Exception))
        for name in ("InvalidDataError", "InvalidAmountError", "InsufficientFundsError",
                     "DuplicateHolderError", "DuplicateAccountError",
                     "HolderNotFoundError", "AccountNotFoundError"):
            self.assertTrue(issubclass(getattr(errors, name), errors.BankError))

    def test_domain_has_no_interface_or_file_dependencies(self):
        domain = Path(__file__).resolve().parents[1] / "bank_app" / "domain"
        for path in domain.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"print", "input", "open"}, path.name)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name.split(".")[0],
                                         {"json", "pathlib", "tkinter"}, path.name)
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse(any(word in (node.module or "").split(".")
                                         for word in ("persistence", "interfaces", "tkinter",
                                                      "json", "pathlib")), path.name)


if __name__ == "__main__":
    unittest.main()
