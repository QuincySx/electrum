import time
from typing import Optional

from electrum_gui.common.basic.functional.require import require
from electrum_gui.common.basic.functional.text import force_text
from electrum_gui.common.basic.request.exceptions import JsonRPCException
from electrum_gui.common.basic.request.json_rpc import JsonRPCRequest
from electrum_gui.common.provider.chains.stc.sdk import starcoin_stdlib
from electrum_gui.common.provider.chains.stc.sdk.starcoin_types import (
    AccountResource,
    BalanceResource,
    TransactionPayload,
)
from electrum_gui.common.provider.chains.stc.sdk.utils import utils as stc_utils
from electrum_gui.common.provider.data import (
    Address,
    BlockHeader,
    ClientInfo,
    EstimatedTimeOnPrice,
    PricesPerUnit,
    Transaction,
    TransactionFee,
    TransactionInput,
    TransactionOutput,
    TransactionStatus,
    TxBroadcastReceipt,
    TxBroadcastReceiptCode,
)
from electrum_gui.common.provider.exceptions import TransactionNotFound
from electrum_gui.common.provider.interfaces import ClientInterface

MAIN_COIN_SYMBOL = f"{stc_utils.CORE_CODE_ADDRESS}::STC::STC"


class StateNotFoundError(ValueError):
    pass


class STCJsonRPC(ClientInterface):
    def __init__(self, url: str, timeout: int = 5, expire_interval: int = 120):
        self.rpc = JsonRPCRequest(url=url, timeout=timeout)
        self.expire_interval = expire_interval

    def get_info(self) -> ClientInfo:
        block_info = self.rpc.call("chain.info", params=[])
        block_number = block_info["head"]["number"]
        block_time = int(block_info["head"]["timestamp"][:-3])
        return ClientInfo(
            "STC_JSON_RPC",
            best_block_number=int(block_number),
            is_ready=int(time.time()) - block_time < self.expire_interval,
        )

    def _get_account_sequence_number(self, addr: str) -> int:
        struct_tag = f"{stc_utils.CORE_CODE_ADDRESS}::Account::Account"
        path = f"{addr}/{stc_utils.RESOURCE_TAG}/{struct_tag}"
        state, next_sequence_number = self.rpc.batch_call(
            [
                ("state.get", [path]),
                ("txpool.next_sequence_number", [addr]),  # if tx not confirmed, get seq from tx pool
            ]
        )
        if state is None:
            raise StateNotFoundError("State not found")
        resource = AccountResource.bcs_deserialize(bytes(state))
        return max(int(resource.sequence_number), next_sequence_number or 0)

    def get_address(self, address: str) -> Address:
        _account_exists = True
        _nonce = 0
        _balance = 0
        try:
            sequence_number = self._get_account_sequence_number(address)
        except StateNotFoundError:
            _account_exists = False
        else:
            _nonce = sequence_number
            _balance = self.get_balance(address)

        return Address(address=address, balance=_balance, nonce=_nonce, existing=_account_exists)

    def get_balance(self, address: str, token_address: Optional[str] = None) -> int:
        struct_tag = f"{stc_utils.CORE_CODE_ADDRESS}::Account::Balance<{token_address or MAIN_COIN_SYMBOL}>"
        path = f"{address}/{stc_utils.RESOURCE_TAG}/{struct_tag}"
        state = self.rpc.call("state.get", params=[path])
        if state is None:
            return 0
        balance = BalanceResource.bcs_deserialize(bytes(state))
        return int(balance.token)

    def get_transaction_by_txid(self, txid: str) -> Transaction:
        pending_tx, tx, receipt = self.rpc.batch_call(
            [
                ("txpool.pending_txn", [txid]),
                ("chain.get_transaction", [txid]),
                ("chain.get_transaction_info", [txid]),
            ],
            ignore_errors=True,
        )

        if pending_tx is None and tx is None:
            raise TransactionNotFound(txid)
        elif pending_tx is not None:
            require(txid == pending_tx.get("transaction_hash"))
            tx = pending_tx.get("raw_txn")
        elif pending_tx is None and tx is not None:
            require(txid == tx.get("transaction_hash"))
            tx = tx.get("user_transaction").get("raw_txn")

        if receipt:
            _block_number = int(receipt.get("block_number"))
            block_info = self.rpc.call("chain.get_block_by_number", [_block_number])
            block_header = BlockHeader(
                block_hash=receipt.get("block_hash", ""),
                block_number=_block_number,
                block_time=int(block_info["header"]["timestamp"][:-3]),
            )
            status = (
                TransactionStatus.CONFIRM_SUCCESS
                if receipt.get("status") == "Executed"
                else TransactionStatus.CONFIRM_REVERTED
            )
            gas_used = int(receipt.get("gas_used", "0"))
        else:
            block_header = None
            status = TransactionStatus.PENDING
            gas_used = None

        _value, _receiver, _token_address = 0, "", None
        try:
            _payload = TransactionPayload.bcs_deserialize(bytes.fromhex(tx.get("payload")[2:]))
            _script_function_call = starcoin_stdlib.decode_script_function_payload(_payload)
            if isinstance(
                _script_function_call,
                (
                    starcoin_stdlib.ScriptFunctionCall__PeerToPeer,
                    starcoin_stdlib.ScriptFunctionCall__PeerToPeerV2,
                    # starcoin_stdlib.ScriptFunctionCall__AcceptToken, todo parse accept token tx
                ),
            ):
                _value = int(_script_function_call.amount[0])
                _receiver = _script_function_call.payee[0].bcs_serialize().hex()
                _token_type = _script_function_call.token_type.value
                _token_address = (
                    f"{'0x' + stc_utils.account_address_hex(_token_type.address)}::"
                    f"{_token_type.module.value}::{_token_type.name.value}"
                )
                if _token_address == MAIN_COIN_SYMBOL:
                    _token_address = None
        except ValueError:
            pass
        gas_limit = int(tx.get("max_gas_amount", "0"))
        fee = TransactionFee(
            limit=gas_limit,
            used=gas_used or gas_limit,
            price_per_unit=int(tx.get("gas_unit_price", "0")),
        )
        sender = tx.get("sender", "")

        return Transaction(
            txid=txid,
            inputs=[TransactionInput(address=sender, value=_value, token_address=_token_address)],
            outputs=[TransactionOutput(address="0x" + _receiver, value=_value, token_address=_token_address)],
            status=status,
            block_header=block_header,
            fee=fee,
            nonce=int(tx["sequence_number"]),
        )

    def broadcast_transaction(self, raw_tx: str) -> TxBroadcastReceipt:
        txid, is_success, receipt_code, receipt_message = None, False, TxBroadcastReceiptCode.UNKNOWN, ""

        try:
            txid = self.rpc.call("txpool.submit_hex_transaction", params=[raw_tx])
            is_success, receipt_code = True, TxBroadcastReceiptCode.SUCCESS
        except JsonRPCException as e:
            json_response = e.json_response
            receipt_code, receipt_message = TxBroadcastReceiptCode.UNEXPECTED_FAILED, force_text(json_response)

            if isinstance(json_response, dict) and "error" in json_response:
                error_message = json_response.get("error", dict()).get("message", "")
                receipt_message = error_message

                if "SEQUENCE_NUMBER_TOO_OLD" in error_message:
                    receipt_code = TxBroadcastReceiptCode.NONCE_TOO_LOW

        return TxBroadcastReceipt(
            txid=txid,
            is_success=is_success,
            receipt_code=receipt_code,
            receipt_message=receipt_message,
        )

    def get_prices_per_unit_of_fee(self) -> PricesPerUnit:
        resp = self.rpc.call("txpool.gas_price", params=[])

        price = max(int(resp), 1)
        normal = EstimatedTimeOnPrice(price=price, time=60)

        return PricesPerUnit(normal=normal)

    def estimate_gas_limit(self, params=dict) -> int:
        resp = self.rpc.call("contract.dry_run", params=[params])
        if resp.get("status") == 'Executed':
            return int(resp.get("gas_used"))
        else:
            return 0
