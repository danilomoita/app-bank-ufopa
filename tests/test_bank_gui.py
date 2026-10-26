"""Testes dos widgets reais de Tkinter, com janela oculta e JSON temporário."""

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

from bank_app.domain.account import Account
from bank_app.domain.bank import Bank
from bank_app.persistence.database import Database


class GuiTests(unittest.TestCase):
    def setUp(self):
        if importlib.util.find_spec("bank_app.interfaces.bank_gui") is None:
            self.fail("bank_gui.py ainda não implementado")
        from bank_app.interfaces.bank_gui import BankApp
        self.bank = Bank()
        self.database = Mock(spec=Database)
        self.app = BankApp(self.bank, self.database, visible=False)
        self.addCleanup(self.app.destroy)
        self.error = self.enterContext(patch(
            "bank_app.interfaces.bank_gui.messagebox.showerror"
        ))
        self.confirm = self.enterContext(patch(
            "bank_app.interfaces.bank_gui.messagebox.askyesno", return_value=True
        ))
        self.app.update_idletasks()

    def select_holder(self, holder):
        self.app.refresh_holders()
        self.app.holders_tree.selection_set(str(id(holder)))
        self.app.refresh_accounts()

    def select_account(self, account):
        self.app.refresh_accounts()
        self.app.accounts_tree.selection_set(str(account.number))
        self.app.accounts_tree.event_generate("<<TreeviewSelect>>")
        self.app.update()

    def prepare_account(self):
        holder = self.bank.create_holder("Ana Silva", "111")
        self.bank.create_account(holder)
        account = holder.get_account(1)
        self.select_holder(holder)
        self.select_account(account)
        return holder, account

    def test_tk_subclass_and_injected_dependencies(self):
        self.assertIsInstance(self.app, tk.Tk)
        self.assertIs(self.app.bank, self.bank)
        self.assertIs(self.app.database, self.database)
        self.database.load.assert_not_called()
        self.assertEqual(len(self.app.panes.panes()), 2)
        self.assertTrue(self.app.new_account_button.instate(["disabled"]))
        self.assertTrue(self.app.deposit_button.instate(["disabled"]))

    def test_create_holder_button_saves_and_refreshes(self):
        self.app.name_var.set("João")
        self.app.cpf_var.set("111")
        self.app.create_holder_button.invoke()
        self.assertEqual(next(self.bank.holders()).name, "João")
        self.assertEqual(len(self.app.holders_tree.get_children()), 1)
        self.database.save.assert_called_once_with(self.bank)
        self.assertEqual(self.app.name_var.get(), "")
        self.assertIn("cadastrado", self.app.status_var.get())

    def test_invalid_or_duplicate_holder_displays_bank_error(self):
        self.bank.create_holder("Ana", "111")
        for name in ("", "Bia"):
            self.app.name_var.set(name)
            self.app.cpf_var.set("111")
            self.app.create_holder()
        self.assertEqual(self.error.call_count, 2)
        self.database.save.assert_not_called()
        self.assertEqual(len(list(self.bank.holders())), 1)

    def test_search_updates_reactively_and_empty_lists_all(self):
        self.bank.create_holder("Ana Silva", "111")
        self.bank.create_holder("Bia Costa", "222")
        self.app.refresh_holders()
        self.app.search_var.set("sILVa")
        self.assertEqual([h.name for h in self.app.holders], ["Ana Silva"])
        self.app.search_var.set("")
        self.assertEqual(len(self.app.holders_tree.get_children()), 2)
        self.app.search_var.set("ausente")
        self.assertEqual(self.app.holders_tree.get_children(), ())
        self.database.save.assert_not_called()

    def test_holder_selection_lists_only_own_accounts(self):
        first = self.bank.create_holder("Ana", "111")
        second = self.bank.create_holder("Bia", "222")
        self.bank.create_account(first)
        self.bank.create_account(second)
        self.select_holder(first)
        self.assertEqual(self.app.accounts_tree.get_children(), ("1",))
        self.assertFalse(self.app.new_account_button.instate(["disabled"]))
        self.select_holder(second)
        self.assertEqual(self.app.accounts_tree.get_children(), ("2",))
        self.assertIsNone(self.app.selected_account())

    def test_filtering_out_selected_holder_clears_accounts(self):
        self.prepare_account()
        self.app.search_var.set("ausente")
        self.app.update()
        self.assertIsNone(self.app.selected_holder())
        self.assertIsNone(self.app.selected_account())
        self.assertEqual(self.app.accounts_tree.get_children(), ())
        self.assertTrue(self.app.deposit_button.instate(["disabled"]))

    def test_create_account_button_saves_and_refreshes(self):
        holder = self.bank.create_holder("Ana", "111")
        self.select_holder(holder)
        self.app.new_account_button.invoke()
        self.assertEqual(holder.get_account(1).balance, 0)
        self.assertEqual(self.app.accounts_tree.get_children(), ("1",))
        self.database.save.assert_called_once_with(self.bank)

    def test_missing_selection_does_not_change_or_save(self):
        self.app.create_account()
        self.app.delete_account()
        self.app.transaction(Account.deposit)
        self.database.save.assert_not_called()
        self.assertEqual(self.error.call_count, 3)

    def test_delete_confirmation_cancel_preserves_account(self):
        holder, account = self.prepare_account()
        self.confirm.return_value = False
        self.app.delete_account_button.invoke()
        self.assertIs(holder.get_account(1), account)
        self.database.save.assert_not_called()
        self.confirm.assert_called_once()

    def test_confirmed_delete_saves_and_clears_selection(self):
        holder, _ = self.prepare_account()
        self.app.delete_account_button.invoke()
        self.assertEqual(list(holder.accounts()), [])
        self.assertEqual(self.app.accounts_tree.get_children(), ())
        self.assertIsNone(self.app.selected_account())
        self.database.save.assert_called_once_with(self.bank)

    def test_deposit_and_withdraw_buttons_with_decimal_separators(self):
        _, account = self.prepare_account()
        self.app.amount_var.set("0,30")
        self.app.deposit_button.invoke()
        self.app.update()
        self.assertIs(self.app.selected_account(), account)
        self.app.amount_var.set("0.10")
        self.app.withdraw_button.invoke()
        self.assertEqual(account.balance, 0.20)
        self.assertEqual(self.database.save.call_count, 2)
        self.assertIn("0,20", str(self.app.accounts_tree.item("1", "values")))

    def test_selected_account_summary_uses_brazilian_currency(self):
        _, account = self.prepare_account()
        self.app.amount_var.set("1250,50")
        self.app.deposit_button.invoke()
        self.app.update()
        self.assertEqual(account.balance, 1250.50)
        self.assertEqual(self.app.balance_var.get(), "R$ 1.250,50")
        self.assertIn("0001", self.app.selected_account_var.get())
        self.assertIn("1.250,50", str(self.app.accounts_tree.item("1", "values")))
        self.app.search_var.set("ausente")
        self.app.update()
        self.assertEqual(self.app.balance_var.get(), "—")
        self.assertIn("Selecione", self.app.selected_account_var.get())

    def test_input_conversion_error_is_separate_from_bank_error(self):
        _, account = self.prepare_account()
        self.app.amount_var.set("texto")
        self.app.transaction(Account.deposit)
        self.assertIn("numérico", self.error.call_args.args[1])
        self.app.amount_var.set("100")
        self.app.transaction(Account.withdraw)
        self.assertIn("Saldo insuficiente", self.error.call_args.args[1])
        self.assertEqual(account.balance, 0)
        self.database.save.assert_not_called()

    def test_invalid_amounts_are_rejected_by_model(self):
        _, account = self.prepare_account()
        for value in ("0", "-1", "nan", "inf"):
            self.app.amount_var.set(value)
            self.app.transaction(Account.deposit)
        self.assertEqual(account.balance, 0)
        self.assertEqual(self.error.call_count, 4)
        self.database.save.assert_not_called()

    def test_save_failure_refreshes_state_and_allows_retry(self):
        self.database.save.side_effect = [PermissionError("sem acesso"), None]
        self.app.name_var.set("Ana")
        self.app.cpf_var.set("111")
        self.app.create_holder()
        self.assertEqual(len(self.app.holders_tree.get_children()), 1)
        self.assertIn("não salvos", self.app.status_var.get())
        self.assertFalse(self.app.retry_save_button.instate(["disabled"]))
        self.app.retry_save_button.invoke()
        self.assertEqual(self.database.save.call_count, 2)
        self.assertTrue(self.app.retry_save_button.instate(["disabled"]))
        self.assertFalse(self.app._unsaved_changes)

    def test_close_can_cancel_after_save_failure(self):
        self.app._unsaved_changes = True
        self.database.save.side_effect = PermissionError("sem acesso")
        self.confirm.return_value = False
        self.app.close()
        self.assertTrue(self.app.winfo_exists())
        self.confirm.assert_called_once()

    def test_round_trip_with_real_database(self):
        with TemporaryDirectory() as directory:
            self.app.database = Database(Path(directory) / "bank.json")
            self.app.name_var.set("João")
            self.app.cpf_var.set("111")
            self.app.create_holder()
            holder = next(self.bank.holders())
            self.select_holder(holder)
            self.app.create_account()
            self.select_account(holder.get_account(1))
            self.app.amount_var.set("25,50")
            self.app.deposit_button.invoke()
            loaded = self.app.database.load()
            self.assertEqual(next(loaded.holders()).get_account(1).balance, 25.50)


if __name__ == "__main__":
    unittest.main()
