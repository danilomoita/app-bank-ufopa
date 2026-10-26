"""Interface Tkinter: apresentação e eventos, sem regras de negócio ou arquivos."""

from collections.abc import Callable
import tkinter as tk
from tkinter import font as tkfont, messagebox, ttk

from ..domain.account import Account
from ..domain.bank import Bank
from ..domain.exceptions import BankError
from ..domain.holder import Holder
from ..persistence.database import Database


class BankApp(tk.Tk):
    """Janela do banco, utilizando o mesmo modelo e persistência do terminal."""

    def __init__(self, bank: Bank, database: Database, *, visible: bool = True):
        super().__init__()
        # Construir oculta evita exibir uma janela incompleta; ajuda nos testes.
        self.withdraw()
        self.bank = bank
        self.database = database
        self.holders: list[Holder] = []
        self._holders_by_id: dict[str, Holder] = {}
        self._accounts_by_id: dict[str, Account] = {}
        self._displayed_holder: Holder | None = None
        self._unsaved_changes = False

        self.title("Banco App — UFOPA")
        width = min(1180, self.winfo_screenwidth() - 80)
        height = min(800, self.winfo_screenheight() - 100)
        self.geometry(f"{width}x{height}")
        self.minsize(min(980, width), min(700, height))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.search_var = tk.StringVar(self)
        self.name_var = tk.StringVar(self)
        self.cpf_var = tk.StringVar(self)
        self.amount_var = tk.StringVar(self)
        self.status_var = tk.StringVar(self, value="Pronto. Cadastre ou selecione um titular.")
        self.accounts_title_var = tk.StringVar(self, value="Contas — selecione um titular")
        self.holder_count_var = tk.StringVar(self, value="0 titulares")
        self.account_count_var = tk.StringVar(self, value="0 contas")
        self.selected_account_var = tk.StringVar(self, value="Selecione uma conta")
        self.balance_var = tk.StringVar(self, value="—")
        self.status_kind_var = tk.StringVar(self, value="Pronto")

        self._configure_styles()

        header = ttk.Frame(self, padding=(24, 18), style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Banco App", style="HeaderTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(header, text="Seu banco acadêmico", style="HeaderSubtitle.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(header, text="UFOPA  /  POO EM PYTHON", style="HeaderBadge.TLabel").grid(
            row=0, column=1, rowspan=2, sticky="e"
        )

        toolbar = ttk.Frame(self, padding=(24, 12), style="App.TFrame")
        toolbar.grid(row=1, column=0, sticky="ew")
        toolbar.columnconfigure(0, weight=1)
        ttk.Label(toolbar, text="Visão geral", style="PageTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(toolbar, text="Ctrl+F  Buscar     Ctrl+N  Novo titular", style="AppHint.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        self.panes = ttk.Panedwindow(self, orient=tk.HORIZONTAL, style="Workspace.TPanedwindow")
        self.panes.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 12))
        self.build_holders_panel()
        self.build_accounts_panel()

        footer = ttk.Frame(self, padding=(20, 10), style="App.TFrame")
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(1, weight=1)
        self.status_badge = ttk.Label(
            footer, textvariable=self.status_kind_var, style="InfoBadge.TLabel"
        )
        self.status_badge.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.status_label = ttk.Label(
            footer, textvariable=self.status_var, wraplength=650, style="AppHint.TLabel"
        )
        self.status_label.grid(row=0, column=1, sticky="w")
        self.bind("<Configure>", self._resize_status, add="+")
        self.retry_save_button = ttk.Button(
            footer, text="Salvar novamente", command=self.save, state="disabled"
        )
        self.retry_save_button.grid(row=0, column=2, padx=(12, 0))

        self.search_var.trace_add("write", self.search_changed)
        self.bind("<Control-f>", self._focus_search)
        self.bind("<Control-n>", self._focus_new_holder)
        self.bind("<Control-s>", self._save_shortcut)
        self.refresh_holders()
        if visible:
            self.deiconify()

    def _configure_styles(self) -> None:
        """Personaliza apenas widgets padrão; não exige fontes ou temas externos."""
        self.style = ttk.Style(self)
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")
        family = tkfont.nametofont("TkDefaultFont", root=self).actual("family")
        self.configure(background="#F2F5FA")
        style = self.style
        style.configure(".", font=(family, 10), background="white", foreground="#172D49")
        style.configure("App.TFrame", background="#F2F5FA")
        style.configure("Card.TFrame", background="white", relief="solid", borderwidth=1,
                        bordercolor="#DDE5F0")
        style.configure("Header.TFrame", background="#142A46")
        style.configure("HeaderTitle.TLabel", background="#142A46", foreground="white",
                        font=(family, 24, "bold"))
        style.configure("HeaderSubtitle.TLabel", background="#142A46", foreground="#C2D2E7")
        style.configure("HeaderBadge.TLabel", background="#243E5D", foreground="#E2ECF9",
                        padding=(14, 9), font=(family, 9, "bold"))
        style.configure("PageTitle.TLabel", background="#F2F5FA", font=(family, 13, "bold"))
        style.configure("AppHint.TLabel", background="#F2F5FA", foreground="#52647B")
        style.configure("Section.TLabel", font=(family, 15, "bold"))
        style.configure("FormTitle.TLabel", font=(family, 11, "bold"))
        style.configure("Muted.TLabel", foreground="#52647B")
        style.configure("Count.TLabel", background="#EDF3FC", foreground="#2458AB",
                        padding=(9, 4), font=(family, 9, "bold"))
        style.configure("Hero.TFrame", background="#EDF3FC")
        style.configure("HeroCaption.TLabel", background="#EDF3FC", foreground="#52647B",
                        font=(family, 9))
        style.configure("HeroNumber.TLabel", background="#EDF3FC", font=(family, 12, "bold"))
        style.configure("HeroBalance.TLabel", background="#EDF3FC", foreground="#173E78",
                        font=(family, 23, "bold"))
        style.configure("Workspace.TPanedwindow", background="#F2F5FA", sashwidth=14)
        style.configure("TEntry", padding=(9, 7), fieldbackground="white",
                        bordercolor="#B8C5D7", lightcolor="white", darkcolor="white")
        style.map("TEntry", bordercolor=[("focus", "#245BC4")],
                  fieldbackground=[("disabled", "#F2F5FA")])
        style.configure("TButton", padding=(12, 8), background="white", foreground="#234B85",
                        bordercolor="#B8C5D7", font=(family, 10, "bold"), focusthickness=2,
                        focuscolor="#245BC4")
        style.map("TButton", background=[("disabled", "#F0F3F7"), ("pressed", "#DAE6F7"),
                                         ("active", "#EAF1FB")],
                  foreground=[("disabled", "#7A8799")])
        style.configure("Primary.TButton", background="#245BC4", foreground="white",
                        bordercolor="#245BC4", focuscolor="white")
        style.map("Primary.TButton", background=[("disabled", "#E1E7F0"),
                                                 ("pressed", "#17408E"), ("active", "#1B4DA9")],
                  foreground=[("disabled", "#6E7F96"), ("!disabled", "white")])
        style.configure("Danger.TButton", foreground="#A32636", bordercolor="#E1BAC1")
        style.map("Danger.TButton", background=[("disabled", "#F0F3F7"),
                                                ("pressed", "#F5D8DD"), ("active", "#FFF0F2")],
                  foreground=[("disabled", "#7A8799"), ("!disabled", "#A32636")])
        style.configure("Treeview", rowheight=34, background="white", fieldbackground="white",
                        borderwidth=0, foreground="#253A55")
        style.configure("Treeview.Heading", padding=(10, 9), background="#F0F4FA",
                        foreground="#405575", font=(family, 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#DDEAFF")],
                  foreground=[("selected", "#163D7B")])
        style.map("Treeview.Heading", background=[("active", "#E5ECF7")])
        for kind, background, foreground in (
            ("Info", "#E6EDF7", "#345078"), ("Success", "#DFF1E8", "#176344"),
            ("Error", "#FCE4E8", "#9F2435"), ("Pending", "#FFF0CE", "#79540A"),
        ):
            style.configure(f"{kind}Badge.TLabel", background=background, foreground=foreground,
                            padding=(10, 5), font=(family, 9, "bold"))

    @staticmethod
    def _format_money(value: float) -> str:
        """Formata a apresentação sem depender do locale instalado no computador."""
        return f"R$ {value:,.2f}".translate(str.maketrans({",": ".", ".": ","}))

    def _resize_status(self, event: tk.Event) -> None:
        if event.widget is self:
            self.status_label.configure(wraplength=max(250, event.width - 360))

    def _focus_search(self, _event: tk.Event | None = None) -> str:
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, tk.END)
        return "break"

    def _focus_new_holder(self, _event: tk.Event | None = None) -> str:
        self.name_entry.focus_set()
        return "break"

    def _save_shortcut(self, _event: tk.Event | None = None) -> str:
        self.save()
        return "break"

    def build_holders_panel(self) -> None:
        """Monta busca, lista e formulário de cadastro de titulares."""
        panel = ttk.Frame(self.panes, padding=18, style="Card.TFrame")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)
        self.panes.add(panel, weight=4)

        title = ttk.Frame(panel)
        title.grid(row=0, column=0, sticky="ew")
        title.columnconfigure(0, weight=1)
        ttk.Label(title, text="Titulares", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(title, textvariable=self.holder_count_var, style="Count.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        ttk.Label(panel, text="Encontre um titular ou faça um novo cadastro.",
                  style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 14))
        search = ttk.Frame(panel)
        search.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        search.columnconfigure(0, weight=1)
        ttk.Label(search, text="Buscar por nome").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.search_entry = ttk.Entry(search, textvariable=self.search_var)
        self.search_entry.grid(row=1, column=0, sticky="ew")
        ttk.Button(search, text="Limpar", command=lambda: self.search_var.set("")).grid(
            row=1, column=1, padx=(8, 0)
        )
        self.search_entry.bind("<Escape>", lambda _event: self.search_var.set(""))
        listing = ttk.Frame(panel)
        listing.grid(row=3, column=0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(0, weight=1)
        self.holders_tree = ttk.Treeview(
            listing, columns=("name", "cpf"), show="headings", selectmode="browse", height=5
        )
        self.holders_tree.heading("name", text="Nome")
        self.holders_tree.heading("cpf", text="CPF")
        self.holders_tree.column("name", width=220, minwidth=130)
        self.holders_tree.column("cpf", width=155, minwidth=120)
        self.holders_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(listing, orient=tk.VERTICAL, command=self.holders_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.holders_tree.configure(yscrollcommand=scrollbar.set)
        self.holders_tree.tag_configure("even", background="#FFFFFF")
        self.holders_tree.tag_configure("odd", background="#F5F8FC")
        self.holders_tree.bind("<<TreeviewSelect>>", lambda _event: self.refresh_accounts())
        self.holders_empty_label = ttk.Label(
            listing, style="Muted.TLabel", anchor="center", justify="center", wraplength=270
        )

        ttk.Separator(panel).grid(row=4, column=0, sticky="ew", pady=16)
        form = ttk.Frame(panel)
        form.grid(row=5, column=0, sticky="ew")
        form.columnconfigure(0, weight=2)
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Novo titular", style="FormTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        ttk.Label(form, text="Nome completo").grid(row=1, column=0, sticky="w", pady=(0, 5))
        ttk.Label(form, text="CPF").grid(row=1, column=1, sticky="w", pady=(0, 5))
        self.name_entry = ttk.Entry(form, textvariable=self.name_var)
        self.name_entry.grid(row=2, column=0, sticky="ew", padx=(0, 10))
        self.cpf_entry = ttk.Entry(form, textvariable=self.cpf_var)
        self.cpf_entry.grid(row=2, column=1, sticky="ew")
        self.name_entry.bind("<Return>", lambda _event: self.cpf_entry.focus_set())
        self.cpf_entry.bind("<Return>", self._create_holder_from_keyboard)
        self.create_holder_button = ttk.Button(
            form, text="Cadastrar titular", command=self.create_holder, style="Primary.TButton"
        )
        self.create_holder_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def build_accounts_panel(self) -> None:
        """Monta lista de contas, ações de cadastro e formulário de transação."""
        panel = ttk.Frame(self.panes, padding=18, style="Card.TFrame")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)
        self.panes.add(panel, weight=5)
        title = ttk.Frame(panel)
        title.grid(row=0, column=0, sticky="ew")
        title.columnconfigure(0, weight=1)
        ttk.Label(title, text="Contas", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(title, textvariable=self.account_count_var, style="Count.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        ttk.Label(panel, textvariable=self.accounts_title_var, wraplength=390,
                  style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 12))

        summary = ttk.Frame(panel, padding=(14, 12), style="Hero.TFrame")
        summary.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        summary.columnconfigure(1, weight=1)
        ttk.Label(summary, text="Conta selecionada", style="HeroCaption.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(summary, text="Saldo disponível", style="HeroCaption.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        ttk.Label(summary, textvariable=self.selected_account_var, style="HeroNumber.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=(6, 0)
        )
        ttk.Label(summary, textvariable=self.balance_var, style="HeroBalance.TLabel").grid(
            row=1, column=1, sticky="e", pady=(6, 0)
        )

        listing = ttk.Frame(panel)
        listing.grid(row=3, column=0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(0, weight=1)
        self.accounts_tree = ttk.Treeview(
            listing, columns=("number", "balance"), show="headings", selectmode="browse", height=4
        )
        self.accounts_tree.heading("number", text="Conta")
        self.accounts_tree.heading("balance", text="Saldo")
        self.accounts_tree.column("number", width=140, minwidth=80)
        self.accounts_tree.column("balance", width=210, minwidth=120, anchor="e")
        self.accounts_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(listing, orient=tk.VERTICAL, command=self.accounts_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.accounts_tree.configure(yscrollcommand=scrollbar.set)
        self.accounts_tree.tag_configure("even", background="#FFFFFF")
        self.accounts_tree.tag_configure("odd", background="#F5F8FC")
        self.accounts_tree.bind("<<TreeviewSelect>>", lambda _event: self._update_actions())
        self.accounts_tree.bind("<Return>", self._focus_amount)
        self.accounts_empty_label = ttk.Label(
            listing, style="Muted.TLabel", anchor="center", justify="center", wraplength=280
        )

        actions = ttk.Frame(panel)
        actions.grid(row=4, column=0, sticky="ew", pady=12)
        self.new_account_button = ttk.Button(actions, text="Nova conta", command=self.create_account)
        self.new_account_button.pack(side=tk.LEFT)
        self.delete_account_button = ttk.Button(
            actions, text="Excluir conta", command=self.delete_account, style="Danger.TButton"
        )
        self.delete_account_button.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Separator(panel).grid(row=5, column=0, sticky="ew", pady=(2, 12))
        form = ttk.Frame(panel)
        form.grid(row=6, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Movimentar conta", style="FormTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        ttk.Label(form, text="Valor (R$)").grid(row=1, column=0, padx=(0, 8), sticky="w")
        self.amount_entry = ttk.Entry(form, textvariable=self.amount_var)
        self.amount_entry.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(form, text="Use vírgula ou ponto decimal. Ex.: 25,50").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=0, columnspan=2, sticky="ew")
        buttons.columnconfigure((0, 1), weight=1)
        # Os botões recebem métodos do modelo; não calculam nem validam saldos.
        self.deposit_button = ttk.Button(
            buttons, text="Depositar", command=lambda: self.transaction(Account.deposit),
            style="Primary.TButton"
        )
        self.deposit_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.withdraw_button = ttk.Button(
            buttons, text="Sacar", command=lambda: self.transaction(Account.withdraw)
        )
        self.withdraw_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def _create_holder_from_keyboard(self, _event: tk.Event) -> str:
        self.create_holder()
        return "break"

    def _focus_amount(self, _event: tk.Event) -> str:
        if self.selected_account() is not None:
            self.amount_entry.focus_set()
        return "break"

    def selected_holder(self) -> Holder | None:
        """Traduz a seleção visual para o objeto original do modelo."""
        selection = self.holders_tree.selection()
        return self._holders_by_id.get(selection[0]) if selection else None

    def selected_account(self) -> Account | None:
        """Retorna a conta selecionada apenas para o titular atualmente exibido."""
        if self.selected_holder() is not self._displayed_holder:
            return None
        selection = self.accounts_tree.selection()
        return self._accounts_by_id.get(selection[0]) if selection else None

    def _update_actions(self) -> None:
        """Habilita ações conforme a seleção; isso é estado da interface."""
        holder = self.selected_holder()
        account = self.selected_account()
        self.new_account_button.state(["!disabled"] if holder is not None else ["disabled"])
        for button in (self.delete_account_button, self.deposit_button, self.withdraw_button):
            button.state(["!disabled"] if account is not None else ["disabled"])
        self.amount_entry.state(["!disabled"] if account is not None else ["disabled"])
        if account is not None:
            self.selected_account_var.set(f"Conta {account}")
            self.balance_var.set(self._format_money(account.balance))
        else:
            self.selected_account_var.set("Selecione uma conta")
            self.balance_var.set("—")

    def refresh_holders(self) -> None:
        """Atualiza a lista filtrada, preservando a seleção se ainda estiver visível."""
        previous = self.selected_holder()
        self.holders = list(self.bank.filter_by_name(self.search_var.get()))
        self._holders_by_id.clear()
        for item in self.holders_tree.get_children():
            self.holders_tree.delete(item)
        for index, holder in enumerate(self.holders):
            key = str(id(holder))
            self._holders_by_id[key] = holder
            self.holders_tree.insert(
                "", tk.END, iid=key, values=(holder.name, holder.cpf),
                tags=("even" if index % 2 == 0 else "odd",),
            )
        count = len(self.holders)
        self.holder_count_var.set(f"{count} titular" if count == 1 else f"{count} titulares")
        if self.holders:
            self.holders_empty_label.place_forget()
        else:
            text = ("Nenhum titular encontrado.\nTente outro nome ou limpe a busca."
                    if self.search_var.get() else
                    "Seu primeiro cadastro começa aqui.\nPreencha nome e CPF abaixo.")
            self.holders_empty_label.configure(text=text)
            self.holders_empty_label.place(relx=0.5, rely=0.58, anchor="center", relwidth=0.9)
        if previous is not None and str(id(previous)) in self._holders_by_id:
            self.holders_tree.selection_set(str(id(previous)))
        self.refresh_accounts()

    def refresh_accounts(self, keep: int | None = None) -> None:
        """Relê as contas do modelo; mantém a seleção após depósitos e saques."""
        previous = self.selected_account()
        if keep is None and previous is not None:
            keep = previous.number
        holder = self.selected_holder()
        self._displayed_holder = holder
        self._accounts_by_id.clear()
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        if holder is not None:
            self.accounts_title_var.set(f"Contas de {holder.name}")
            for index, account in enumerate(holder.accounts()):
                key = str(account.number)
                self._accounts_by_id[key] = account
                self.accounts_tree.insert(
                    "", tk.END, iid=key, values=(str(account), self._format_money(account.balance)),
                    tags=("even" if index % 2 == 0 else "odd",),
                )
        else:
            self.accounts_title_var.set("Contas — selecione um titular")
        count = len(self._accounts_by_id)
        self.account_count_var.set(f"{count} conta" if count == 1 else f"{count} contas")
        if count:
            self.accounts_empty_label.place_forget()
        else:
            text = ("Este titular ainda não tem contas.\nClique em Nova conta para começar."
                    if holder is not None else
                    "Selecione um titular no painel ao lado\npara visualizar suas contas.")
            self.accounts_empty_label.configure(text=text)
            self.accounts_empty_label.place(relx=0.5, rely=0.60, anchor="center", relwidth=0.9)
        if keep is not None and str(keep) in self._accounts_by_id:
            self.accounts_tree.selection_set(str(keep))
        self._update_actions()

    def search_changed(self, *_args: str) -> None:
        """O trace da variável executa a filtragem sempre que o texto muda."""
        self.refresh_holders()

    def _show_error(self, message: str, title: str = "Erro do banco") -> None:
        self._set_status(message, "error")
        messagebox.showerror(title, message, parent=self)

    def _set_status(self, message: str, kind: str = "info") -> None:
        """Texto e cor comunicam o estado, sem depender exclusivamente da cor."""
        labels = {"info": ("Pronto", "Info"), "success": ("Sucesso", "Success"),
                  "error": ("Erro", "Error"), "pending": ("Pendente", "Pending")}
        label, style = labels[kind]
        self.status_kind_var.set(label)
        self.status_badge.configure(style=f"{style}Badge.TLabel")
        self.status_var.set(message)

    def save(self, message: str = "Dados salvos.") -> bool:
        """Delega toda a gravação à persistência e atualiza status e recuperação."""
        try:
            self.database.save(self.bank)
        except OSError as error:
            self._unsaved_changes = True
            self.retry_save_button.state(["!disabled"])
            self._show_error(
                f"Não foi possível salvar: {error}\nUse 'Salvar novamente'.",
                "Falha ao salvar",
            )
            self._set_status(
                "Alterações em memória; dados não salvos. Tente salvar novamente.", "pending"
            )
            return False
        self._unsaved_changes = False
        self.retry_save_button.state(["disabled"])
        self._set_status(message, "success")
        return True

    def _perform_change(self, operation: Callable[[], object], message: str) -> bool:
        """Trata erros e salva após uma alteração aceita pelo modelo."""
        try:
            operation()
        except BankError as error:
            self._show_error(str(error))
            return False
        except ValueError:
            self._show_error("Digite um valor numérico válido.", "Valor inválido")
            return False
        self._unsaved_changes = True
        self.save(message)
        # A tela deve refletir a alteração em memória mesmo se a gravação falhar.
        return True

    def create_holder(self) -> None:
        if self._perform_change(
            lambda: self.bank.create_holder(self.name_var.get(), self.cpf_var.get()),
            "Titular cadastrado e dados salvos.",
        ):
            self.name_var.set("")
            self.cpf_var.set("")
            self.search_var.set("")  # O trace exibe todos, incluindo o novo titular.

    def create_account(self) -> None:
        holder = self.selected_holder()
        if holder is None:
            self._show_error("Selecione um titular.", "Seleção necessária")
            return
        if self._perform_change(
            lambda: self.bank.create_account(holder), "Conta criada e dados salvos."
        ):
            self.refresh_accounts()

    def delete_account(self) -> None:
        holder, account = self.selected_holder(), self.selected_account()
        if holder is None or account is None:
            self._show_error("Selecione uma conta.", "Seleção necessária")
            return
        if not messagebox.askyesno(
            "Excluir conta", f"Deseja excluir a conta {account}?", parent=self
        ):
            return
        if self._perform_change(
            lambda: holder.delete_account(account.number), "Conta excluída e dados salvos."
        ):
            self.refresh_accounts()

    def transaction(self, operation: Callable[[Account, float], None]) -> None:
        account = self.selected_account()
        if account is None:
            self._show_error("Selecione uma conta.", "Seleção necessária")
            return
        if self._perform_change(
            lambda: operation(account, float(self.amount_var.get().strip().replace(",", "."))),
            "Operação realizada e dados salvos.",
        ):
            self.amount_var.set("")
            self.refresh_accounts(keep=account.number)

    def close(self) -> None:
        """Tenta salvar pendências antes de fechar; descartar exige confirmação."""
        if self._unsaved_changes and not self.save():
            if not messagebox.askyesno(
                "Fechar sem salvar?",
                "As alterações ainda não foram salvas. Deseja fechar e descartá-las?",
                parent=self,
            ):
                return
        self.destroy()


def main() -> int:
    """Carrega o banco e fornece as dependências para a janela."""
    database = Database()
    try:
        bank = database.load()
    except (BankError, OSError, ValueError, TypeError, KeyError) as error:
        # Erro de carga não deve resultar em substituição silenciosa dos dados.
        root = tk.Tk()
        root.withdraw()
        try:
            messagebox.showerror("Falha ao carregar", f"Não foi possível abrir o banco:\n{error}", parent=root)
        finally:
            root.destroy()
        return 1
    app = BankApp(bank, database)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
