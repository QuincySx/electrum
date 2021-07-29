from typing import Any

from electrum_gui.common.basic import exceptions


class TransactionNotFound(Exception):
    def __init__(self, txid: str):
        super(TransactionNotFound, self).__init__(repr(txid))
        self.txid = txid


class NoAvailableClient(Exception):
    def __init__(self, chain_code: str, candidates: list, instance_required: Any):
        super(NoAvailableClient, self).__init__(
            f"chain_code: {repr(chain_code)}, candidates: {candidates}, instance_required: {instance_required}"
        )


class ProviderClassNotFound(Exception):
    def __init__(self, chain_code: str, path: str):
        super(ProviderClassNotFound, self).__init__(f"chain_code: {repr(chain_code)}, path: {path}")


class UnknownBroadcastError(Exception):
    def __init__(self, message: str):
        super(UnknownBroadcastError, self).__init__(f"error message: {message}")


class TransactionAlreadyKnown(UnknownBroadcastError):
    pass


class TransactionNonceTooLow(UnknownBroadcastError):
    pass


class TransactionUnderpriced(UnknownBroadcastError):
    pass


class TransactionGasTooLow(UnknownBroadcastError):
    pass


class TransactionGasLimitExceeded(UnknownBroadcastError):
    pass


class FailedToGetGasPrices(Exception):
    def __init__(self):
        super(FailedToGetGasPrices, self).__init__("Failed to get gas prices.")


class InsufficientBalance(exceptions.OneKeyException):
    key = "msg__insufficient_balance"

    def __init__(self):
        super(InsufficientBalance, self).__init__("Insufficient funds")
