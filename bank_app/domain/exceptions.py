"""Hierarquia de erros do domínio bancário, sem dependência de interfaces."""


class BankError(Exception):
    """Base comum: permite capturar todos os erros bancários com um único except."""


# A herança preserva o tratamento comum e identifica a regra que foi violada.
# As subclasses já herdam de Exception o armazenamento da mensagem do erro.
class InvalidDataError(BankError):
    """Dado obrigatório ausente ou dado incompatível com as regras do banco."""


class InvalidAmountError(BankError):
    """Valor de depósito ou saque inválido."""


class InsufficientFundsError(BankError):
    """O valor solicitado para saque excede o saldo disponível."""


class DuplicateHolderError(BankError):
    """Já existe um titular cadastrado com o CPF informado."""


class DuplicateAccountError(BankError):
    """Já existe uma conta com o número informado."""


class HolderNotFoundError(BankError):
    """O titular informado não pertence ao banco."""


class AccountNotFoundError(BankError):
    """O titular não possui uma conta com o número informado."""
