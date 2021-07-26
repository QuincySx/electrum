import base64
from typing import Dict, Tuple

from trezorlib import btc as trezor_btc
from trezorlib import messages as trezor_messages

from electrum import bitcoin, constants
from electrum_gui.common.basic import bip44
from electrum_gui.common.basic.functional.require import require
from electrum_gui.common.hardware import interfaces as hardware_interfaces
from electrum_gui.common.provider import data as data
from electrum_gui.common.provider import interfaces as interface
from electrum_gui.common.secret import interfaces as secret_interfaces


def _bip44_purpose_to_secret_type(purpose: int) -> int:
    if purpose in (84, 48):
        script_type = trezor_messages.InputScriptType.SPENDWITNESS
    elif purpose == 49:
        script_type = trezor_messages.InputScriptType.SPENDP2SHWITNESS
    else:
        script_type = trezor_messages.InputScriptType.SPENDADDRESS

    return script_type


class BTCProvider(interface.ProviderInterface, interface.HardwareSupportingMixin):
    def verify_address(self, address: str) -> data.AddressValidation:
        is_valid, encoding = False, None

        if bitcoin.is_segwit_address(address):
            is_valid, encoding = True, "P2WPKH"  # Pay To Witness Public Key Hash
        else:
            try:
                address_type, _ = bitcoin.b58_address_to_hash160(address)
            except Exception as e:
                print(f"Illegal address. error: {e}")
            else:
                if address_type == constants.net.ADDRTYPE_P2SH:
                    is_valid, encoding = True, "P2WPKH-P2SH"  # Pay To Script Hash
                elif address_type == constants.net.ADDRTYPE_P2PKH:
                    is_valid, encoding = True, "P2PKH"  # Pay To Public Key Hash

        return data.AddressValidation(
            normalized_address=address if is_valid else "",
            display_address=address if is_valid else "",
            is_valid=is_valid,
            encoding=encoding,
        )

    def pubkey_to_address(self, verifier: secret_interfaces.VerifierInterface, encoding: str = None) -> str:
        require(encoding in ("P2WPKH", "P2WPKH-P2SH", "P2PKH"))
        return bitcoin.pubkey_to_address(encoding.lower(), verifier.get_pubkey(compressed=True).hex())

    def fill_unsigned_tx(self, unsigned_tx: data.UnsignedTx) -> data.UnsignedTx:
        raise NotImplementedError()

    def sign_transaction(
        self, unsigned_tx: data.UnsignedTx, signers: Dict[str, secret_interfaces.SignerInterface]
    ) -> data.SignedTx:
        raise NotImplementedError()

    def get_token_info_by_address(self, token_address: str) -> Tuple[str, str, int]:
        raise NotImplementedError()

    def hardware_get_xpub(
        self,
        hardware_client: hardware_interfaces.HardwareClientInterface,
        bip44_path: bip44.BIP44Path,
        confirm_on_device: bool = False,
    ) -> str:
        purpose = bip44_path.index_of(bip44.BIP44Level.PURPOSE)
        script_type = _bip44_purpose_to_secret_type(purpose)

        return trezor_btc.get_public_node(
            hardware_client,
            n=bip44_path.to_bip44_int_path(),
            show_display=confirm_on_device,
            coin_name=self.chain_info.name,
            script_type=script_type,
        ).xpub

    def hardware_get_address(
        self,
        hardware_client: hardware_interfaces.HardwareClientInterface,
        bip44_path: bip44.BIP44Path,
        confirm_on_device: bool = False,
    ) -> str:
        purpose = bip44_path.index_of(bip44.BIP44Level.PURPOSE)
        script_type = _bip44_purpose_to_secret_type(purpose)

        address = trezor_btc.get_address(
            hardware_client,
            coin_name=self.chain_info.name,
            n=bip44_path.to_bip44_int_path(),
            show_display=confirm_on_device,
            script_type=script_type,
        )
        return address

    def hardware_sign_transaction(
        self,
        hardware_client: hardware_interfaces.HardwareClientInterface,
        unsigned_tx: data.UnsignedTx,
        bip44_path_of_signers: Dict[str, bip44.BIP44Path],
    ) -> data.SignedTx:
        raise NotImplementedError

    def hardware_sign_message(
        self,
        hardware_client: hardware_interfaces.HardwareClientInterface,
        message: str,
        signer_bip44_path: bip44.BIP44Path,
    ) -> str:
        purpose = signer_bip44_path.index_of(bip44.BIP44Level.PURPOSE)
        script_type = _bip44_purpose_to_secret_type(purpose)

        signature_bytes = trezor_btc.sign_message(
            hardware_client,
            coin_name=self.chain_info.name,
            n=signer_bip44_path.to_bip44_int_path(),
            message=message,
            script_type=script_type,
        ).signature
        return base64.b64encode(signature_bytes).decode()

    def hardware_verify_message(
        self,
        hardware_client: hardware_interfaces.HardwareClientInterface,
        address: str,
        message: str,
        signature: str,
    ) -> bool:
        signature_bytes = base64.b64decode(signature)
        return trezor_btc.verify_message(
            hardware_client,
            coin_name=self.chain_info.name,
            address=address,
            signature=signature_bytes,
            message=message,
        )
