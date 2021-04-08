from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional

from electrum_gui.common.coin.data import ChainInfo, CoinInfo
from electrum_gui.common.provider.data import (
    Address,
    AddressValidation,
    ClientInfo,
    PricePerUnit,
    SignedTx,
    Token,
    Transaction,
    TransactionStatus,
    TxBroadcastReceipt,
    TxPaginate,
    UnsignedTx,
)
from electrum_gui.common.provider.exceptions import TransactionNotFound
from electrum_gui.common.secret.interfaces import SignerInterface, VerifierInterface


class ClientInterface(ABC):
    @abstractmethod
    def get_info(self) -> ClientInfo:
        """
        Get information of client
        :return: ClientInfo
        """

    @property
    def is_ready(self) -> bool:
        """
        Is client ready?
        :return: ready or not
        """
        return self.get_info().is_ready

    @abstractmethod
    def get_address(self, address: str) -> Address:
        """
        Get address information by address str
        :param address: address
        :return: Address
        """

    def get_balance(self, address: str, token: Token = None) -> int:
        """
        get address balance
        :param address: address
        :param token: token, optional
        :return: balance
        """
        return self.get_address(address).balance

    @abstractmethod
    def get_transaction_by_txid(self, txid: str) -> Transaction:
        """
        Get transaction by txid
        :param txid: transaction hash
        :return: Transaction
        :raise: raise TransactionNotFound if target tx not found
        """

    def get_transaction_status(self, txid: str) -> TransactionStatus:
        """
        Get transaction status by txid
        :param txid: transaction hash
        :return: TransactionStatus
        """
        try:
            return self.get_transaction_by_txid(txid).status
        except TransactionNotFound:
            return TransactionStatus.UNKNOWN

    @abstractmethod
    def broadcast_transaction(self, raw_tx: str) -> TxBroadcastReceipt:
        """
        push transaction to chain
        :param raw_tx: transaction in str
        :return: txid, optional
        """

    @abstractmethod
    def get_price_per_unit_of_fee(self) -> PricePerUnit:
        """
        get the price per unit of the fee, likes the gas_price on eth
        :return: price per unit
        """


class SearchTransactionMixin(ABC):
    def search_txs_by_address(  # noqa
        self,
        address: str,
        paginate: Optional[TxPaginate] = None,
    ) -> List[Transaction]:
        """
        Search transactions by address
        :param address: address
        :param paginate: paginate supports, optional
        :return: list of Transaction
        """
        return []

    def search_txids_by_address(
        self,
        address: str,
        paginate: Optional[TxPaginate] = None,
    ) -> List[str]:
        """
        Search transaction hash by address
        :param address: address
        :param paginate: paginate supports, optional
        :return: list of txid
        """
        txs = self.search_txs_by_address(address)

        txids = {i.txid for i in txs}
        txids = list(txids)
        return txids


class ProviderInterface(ABC):
    def __init__(
        self,
        chain_info: ChainInfo,
        coins_loader: Callable[[], List[CoinInfo]],
        client_selector: Callable,
    ):
        self.chain_info = chain_info
        self.coins_loader = coins_loader
        self.client_selector = client_selector

    @property
    def client(self):
        return self.client_selector()

    @abstractmethod
    def verify_address(self, address: str) -> AddressValidation:
        """
        Check whether the address can be recognized
        :param address: address
        :return: AddressValidation
        """

    @abstractmethod
    def pubkey_to_address(self, verifier: VerifierInterface, encoding: str = None) -> str:
        """
        Convert pubkey to address
        :param verifier: VerifierInterface
        :param encoding: encoding of address, optional
        :return: address
        """

    @abstractmethod
    def filling_unsigned_tx(self, unsigned_tx: UnsignedTx) -> UnsignedTx:
        """
        Filling unsigned tx as much as possible
        :param unsigned_tx: incomplete UnsignedTx
        :return: filled UnsignedTx
        """

    @abstractmethod
    def sign_transaction(self, unsigned_tx: UnsignedTx, key_mapping: Dict[str, SignerInterface]) -> SignedTx:
        """
        Sign transaction
        :param unsigned_tx: complete UnsignedTx
        :param key_mapping: mapping of address to SignerInterface
        :return: SignedTx
        """
