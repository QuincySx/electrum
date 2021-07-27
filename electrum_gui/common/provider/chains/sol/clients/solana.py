from typing import List, Optional, Tuple

import spl.token.instructions as spl_token
from solana.publickey import PublicKey

from electrum_gui.common.basic.functional.require import require
from electrum_gui.common.basic.request.json_rpc import JsonRPCRequest
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
    TxPaginate,
)
from electrum_gui.common.provider.exceptions import TransactionNotFound
from electrum_gui.common.provider.interfaces import ClientInterface, SearchTransactionMixin


class Solana(ClientInterface, SearchTransactionMixin):
    def __init__(self, url: str):
        self.rpc = JsonRPCRequest(url)

    def get_info(self) -> ClientInfo:
        epoch_info, ok = self.rpc.batch_call([("getEpochInfo", []), ("getHealth", [])])
        slot = epoch_info["absoluteSlot"]
        is_ready = ok == "ok"
        return ClientInfo(name="sol", best_block_number=slot, is_ready=is_ready)

    def get_account_info(self, address: str) -> dict:
        response = self.rpc.call("getAccountInfo", [address, {"encoding": "jsonParsed"}])
        return response['value']

    def get_address(self, address: str) -> Address:
        # validate address
        pubkey = PublicKey(address)
        balance = 0
        existing = False
        account_info = self.get_account_info(str(pubkey))
        if account_info is not None:
            balance = account_info["lamports"]
            existing = True
        return Address(address=address, balance=balance, existing=existing)

    def get_transaction_by_txid(self, txid: str) -> Transaction:
        result = self.rpc.call("getConfirmedTransaction", [txid, "jsonParsed"])
        return self._parse_transactions(result, txid)

    def get_fees(self) -> Tuple[int, str]:
        fee_info = self.rpc.call("getFees")
        fee_pre_sig = fee_info["value"]["feeCalculator"]["lamportsPerSignature"]
        recent_blockhash = fee_info["value"]["blockhash"]
        return fee_pre_sig, recent_blockhash

    def get_prices_per_unit_of_fee(self) -> PricesPerUnit:
        lamports_per_sig, _ = self.get_fees()
        fee = EstimatedTimeOnPrice(price=lamports_per_sig, time=60)
        return PricesPerUnit(normal=fee)

    def _get_token_balance(self, owner: str, token_address: str, encoding="jsonParsed") -> int:
        response = self.rpc.call("getTokenAccountsByOwner", [owner, {"mint": token_address}, {"encoding": encoding}])
        balance_int = 0
        for token_account in response['value']:
            info = token_account['account']['data']['parsed']['info']
            assert info['owner'] == owner, "incorrect owner"
            balance_int += int(info['tokenAmount']['amount'])
        return balance_int

    def get_balance(self, address: str, token_address: Optional[str] = None) -> int:
        """
        :param address:
        :param token_address: spl-token mint address
        :return: the balance in format (base unit as int, normal unit as str)
        """
        if token_address is not None:
            owner = address
            return self._get_token_balance(owner, token_address)
        else:
            address = self.get_address(address)
            return address.balance

    def broadcast_transaction(self, raw_tx: str) -> TxBroadcastReceipt:
        signature = self.rpc.call("sendTransaction", [raw_tx, {"encoding": "base64"}])
        return TxBroadcastReceipt(
            is_success=True,
            receipt_code=TxBroadcastReceiptCode.SUCCESS,
            txid=signature,
        )

    def search_txs_by_address(self, address: str, paginate: Optional[TxPaginate] = None) -> List[Transaction]:
        """Retrieve the latest 20 transactions."""
        if paginate:
            # TODO: getSignaturesForAddress need txid
            pass
        response = self.rpc.call("getSignaturesForAddress", [address, {"limit": 20}])
        _batch_body = []
        for transaction in response:
            txid = transaction["signature"]
            _batch_body.append(("getConfirmedTransaction", [txid, "jsonParsed"]))
        results = self.rpc.batch_call(_batch_body, timeout=20)
        txs = []
        for i, res in enumerate(results):
            txs.append(self._parse_transactions(res, _batch_body[i][1][0]))
        return txs

    def get_block_by_slot(self, slot: int) -> Optional[dict]:
        result = self.rpc.call("getConfirmedBlock", [slot])
        return result

    def _parse_transactions(self, result: dict, txid: str) -> Transaction:
        """Parse transaction from raw rpc response

        :param result:
        :param txid:
        :return:
        """
        if result is None:
            raise TransactionNotFound(txid)
        inputs = []
        outputs = []
        for instruction in result["transaction"]["message"]["instructions"]:
            transaction_info = instruction["parsed"]["info"]
            instruction_type = instruction["parsed"]["type"]
            if instruction_type != "transfer":
                continue
            program_id = instruction["programId"]
            from_address = transaction_info["source"]
            to_address = transaction_info["destination"]
            token_address = None
            if program_id == str(spl_token.TOKEN_PROGRAM_ID):
                token_address = result["meta"]["postTokenBalances"][0]["mint"]
                value = transaction_info["amount"]
            elif program_id == str(spl_token.SYS_PROGRAM_ID):
                value = transaction_info["lamports"]
            else:
                continue
            inputs.append(TransactionInput(address=from_address, value=value, token_address=token_address))
            outputs.append(TransactionOutput(address=to_address, value=value, token_address=token_address))
        fee = result["meta"]["fee"]
        slot = result["slot"]
        block_info = self.get_block_by_slot(slot)
        require(block_info is not None, "invalid status")
        block_hash = block_info.get("blockhash")
        return Transaction(
            txid=txid,
            fee=TransactionFee(limit=1, used=1, price_per_unit=fee),
            status=TransactionStatus.CONFIRM_SUCCESS
            if result["meta"]["err"] is None
            else TransactionStatus.CONFIRM_REVERTED,
            block_header=BlockHeader(
                block_time=result["blockTime"],
                block_number=slot,
                block_hash=block_hash,
            ),
            inputs=inputs,
            outputs=outputs,
            raw_tx="",
        )
