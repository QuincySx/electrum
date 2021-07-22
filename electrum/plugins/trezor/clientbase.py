import time
from struct import pack
from typing import Tuple

from electrum import ecc
from electrum.i18n import _
from electrum.util import UserCancelled
from electrum.keystore import bip39_normalize_passphrase
from electrum.bip32 import BIP32Node, convert_bip32_path_to_list_of_uint32 as parse_path
from electrum.logging import Logger
from electrum.plugins.hw_wallet.plugin import OutdatedHwFirmwareException, HardwareClientBase

from trezorlib.client import TrezorClient, PASSPHRASE_ON_DEVICE
from trezorlib.exceptions import TrezorFailure, Cancelled, OutdatedFirmwareError
from trezorlib.messages import WordRequestType, RecoveryDeviceType, ButtonRequestType
from trezorlib import protobuf as trezor_protobuf
from trezorlib import ethereum as trezor_ethereum
from trezorlib import btc as trezor_btc
from trezorlib import device as trezor_device

from trezorlib.customer_ui import CustomerUI

MESSAGES = {
    ButtonRequestType.ConfirmOutput:
        _("Confirm the transaction output on your {} device"),
    ButtonRequestType.ResetDevice:
        _("Complete the initialization process on your {} device"),
    ButtonRequestType.ConfirmWord:
        _("Write down the seed word shown on your {}"),
    ButtonRequestType.WipeDevice:
        _("Confirm on your {} that you want to wipe it clean"),
    ButtonRequestType.ProtectCall:
        _("Confirm on your {} device the message to sign"),
    ButtonRequestType.SignTx:
        _("Confirm the total amount spent and the transaction fee on your {} device"),
    ButtonRequestType.Address:
        _("Confirm wallet address on your {} device"),
    ButtonRequestType._Deprecated_ButtonRequest_PassphraseType:
        _("Choose on your {} device where to enter your passphrase"),
    ButtonRequestType.PassphraseEntry:
        _("Please enter your passphrase on the {} device"),
    'default': _("Check your {} device to continue"),
}


class TrezorClientBase(HardwareClientBase, Logger):
    def __init__(self, transport, handler, plugin):
        HardwareClientBase.__init__(self, plugin=plugin)
        if plugin.is_outdated_fw_ignored():
            TrezorClient.is_outdated = lambda *args, **kwargs: False
        self.client = TrezorClient(transport, ui=self)
        self.device = plugin.device
        self.handler = handler
        Logger.__init__(self)

        self.msg = None
        self.creating_wallet = False

        self.in_flow = False

        self.used()

    def run_flow(self, message=None, creating_wallet=False):
        if self.in_flow:
            raise RuntimeError("Overlapping call to run_flow")

        self.in_flow = True
        self.msg = message
        self.creating_wallet = creating_wallet
        self.prevent_timeouts()
        return self

    def end_flow(self):
        self.in_flow = False
        self.msg = None
        self.creating_wallet = False
        self.handler.finished()
        self.used()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, e, traceback):
        self.end_flow()
        if e is not None:
            if isinstance(e, Cancelled):
                raise UserCancelled() from e
            elif isinstance(e, TrezorFailure):
                raise RuntimeError(str(e)) from e
            elif isinstance(e, OutdatedFirmwareError):
                raise OutdatedHwFirmwareException(e) from e
            else:
                return False
        return True

    @property
    def features(self):
        return self.client.features

    @property
    def features_dict(self):
        return trezor_protobuf.to_dict(self.features)

    def __str__(self):
        return "%s/%s" % (self.label(), self.features.device_id)

    def label(self):
        return self.features.label

    def get_soft_device_id(self):
        return self.features.device_id

    def is_initialized(self):
        return self.features.initialized

    def is_pairable(self):
        return not self.features.bootloader_mode

    def has_usable_connection_with_device(self):
        if self.in_flow:
            return True

        try:
            res = self.client.ping("electrum pinging device")
            assert res == "electrum pinging device"
        except BaseException:
            return False
        return True

    def used(self):
        self.last_operation = time.time()

    def prevent_timeouts(self):
        self.last_operation = float('inf')

    def timeout(self, cutoff):
        '''Time out the client if the last operation was before cutoff.'''
        if self.last_operation < cutoff:
            self.logger.info("timed out")
            self.clear_session()

    def i4b(self, x):
        return pack('>I', x)

    def get_xpub(self, bip32_path=None, xtype=None, creating=False):
        address_n = parse_path(bip32_path)
        with self.run_flow(creating_wallet=creating):
            if xtype == "standard":
                xtype = 'p2pkh'
            node = trezor_btc.get_public_node(self.client, address_n, coin_name=self.plugin.get_coin_name(), script_type=self.plugin.get_trezor_input_script_type(xtype)).node
        return BIP32Node(xtype=xtype if xtype != "p2pkh" else 'standard',
                         eckey=ecc.ECPubkey(node.public_key),
                         chaincode=node.chain_code,
                         depth=node.depth,
                         fingerprint=self.i4b(node.fingerprint),
                         child_number=self.i4b(node.child_num)).to_xpub()

    def get_eth_xpub(self, bip32_path=None):
        address_n = parse_path(bip32_path)
        with self.run_flow(''):
            node = trezor_ethereum.get_public_node(self.client, address_n).node
        # return node.xpub
        return BIP32Node(xtype='standard',
                         eckey=ecc.ECPubkey(node.public_key),
                         chaincode=node.chain_code,
                         depth=node.depth,
                         fingerprint=self.i4b(node.fingerprint),
                         child_number=self.i4b(node.child_num)).to_xpub()

    def apply_settings(self, **kwargs) -> str:
        return trezor_device.apply_settings(self.client, **kwargs)

    def backup(self) -> str:
        with self.run_flow(''):
            return trezor_device.se_backup(self.client).hex()

    def se_proxy(self, message) -> str:
        with self.run_flow(''):
            return trezor_device.se_proxy(self.client, message).hex()

    def se_verify(self, digest: bytes) -> Tuple[str, str]:
        resp = trezor_device.se_verify(self.client, digest)
        return resp.cert.hex(), resp.signature.hex()

    def recovery(self, *args):
        with self.run_flow(''):
            return trezor_device.se_restore(self.client, *args)

    def bx_inquire_whitelist(self, **kwargs):
        with self.run_flow(''):
            return trezor_device.bx_inquire_whitelist(self.client, **kwargs)

    def bx_add_or_delete_whitelist(self, **kwargs):
        with self.run_flow(''):
            return trezor_device.bx_add_or_delete_whitelist(self.client, **kwargs)

    def anti_counterfeiting_verify(self, inputmessage):
        with self.run_flow(_("Confirm anti_counterfeiting_verify on your {} device")):
            return trezor_device.anti_counterfeiting_verify(self.client, inputmessage=inputmessage)

    def toggle_passphrase(self):
        if self.features.passphrase_protection:
            msg = _("Confirm on your {} device to disable passphrases")
        else:
            msg = _("Confirm on your {} device to enable passphrases")
        enabled = not self.features.passphrase_protection
        with self.run_flow(msg):
            trezor_device.apply_settings(self.client, use_passphrase=enabled)

    def change_language(self, language):
        with self.run_flow(_("Confirm the new language on your {} device")):
            trezor_device.apply_settings(self.client, language=language)

    def change_label(self, label):
        with self.run_flow(_("Confirm the new label on your {} device")):
            trezor_device.apply_settings(self.client, label=label)

    def change_homescreen(self, homescreen):
        with self.run_flow(_("Confirm on your {} device to change your home screen")):
            trezor_device.apply_settings(self.client, homescreen=homescreen)

    def set_bixin_app(self, is_bixin):
        with self.run_flow(_("used in oneKey app only")):
            trezor_device.apply_settings(self.client, is_bixinapp=is_bixin)

    def set_pin(self, remove):
        if remove:
            msg = _("Confirm on your {} device to disable PIN protection")
        elif self.features.pin_protection:
            msg = _("Confirm on your {} device to change your PIN")
        else:
            msg = _("Confirm on your {} device to set a PIN")
        with self.run_flow(msg):
            return trezor_device.change_pin(self.client, remove)

    def clear_session(self):
        '''Clear the session to force pin (and passphrase if enabled)
        re-entry.  Does not leak exceptions.'''
        self.logger.info(f"clear session: {self}")
        self.prevent_timeouts()
        try:
            self.client.clear_session()
        except BaseException as e:
            # If the device was removed it has the same effect...
            self.logger.info(f"clear_session: ignoring error {e}")

    def close(self):
        '''Called when Our wallet was closed or the device removed.'''
        self.logger.info("closing client")
        self.clear_session()

    def is_uptodate(self):
        if self.client.is_outdated():
            return False
        return self.client.version >= self.plugin.minimum_firmware

    def get_trezor_model(self):
        """Returns '1' for Trezor One, 'T' for Trezor T."""
        return self.features.model

    def device_model_name(self):
        model = self.get_trezor_model()
        if model == '1':
            return "Trezor One"
        elif model == 'T':
            return "Trezor T"
        return None

    def show_address(self, address_str, script_type, multisig=None, coin='btc'):
        address_n = parse_path(address_str)
        with self.run_flow():
            if coin == 'btc':
                coin_name = self.plugin.get_coin_name()
                return trezor_btc.get_address(
                    self.client,
                    coin_name,
                    address_n,
                    show_display=True,
                    script_type=script_type,
                    multisig=multisig)
            else:
                return trezor_ethereum.get_address(
                    self.client,
                    address_n,
                    show_display=True,
                    multisig=multisig)

    def verify_message(self, address_str, message, sign_info):
        with self.run_flow():
            coin_name = self.plugin.get_coin_name()
            return trezor_btc.verify_message(
                self.client,
                signature=sign_info,
                coin_name=coin_name,
                address=address_str,
                message=message)

    def verify_eth_message(self, address_str, message, sign_info):
        with self.run_flow():
            return trezor_ethereum.verify_message(
                self.client,
                address=address_str,
                signature=sign_info,
                message=message)

    def sign_message(self, address_str, message, script_type=None):
        address_n = parse_path(address_str)
        coin_name = self.plugin.get_coin_name()
        with self.run_flow():
            return trezor_btc.sign_message(
                self.client,
                coin_name,
                address_n,
                message,
                script_type=script_type)

    def sign_eth_message(self, address_str, message):
        address_n = parse_path(address_str)
        with self.run_flow():
            return trezor_ethereum.sign_message(
                self.client,
                address_n,
                message)

    def recover_device(self, recovery_type, *args, **kwargs):
        input_callback = self.mnemonic_callback(recovery_type)
        with self.run_flow():
            return trezor_device.recover(
                self.client,
                *args,
                input_callback=input_callback,
                type=recovery_type,
                **kwargs)

    # ========= Unmodified trezorlib methods =========

    def bixin_backup_device(self):
        with self.run_flow(''):
            return trezor_device.bixin_backup_device(self.client)

    def bixin_load_device(self, *args, **kwargs):
        with self.run_flow(''):
            return trezor_device.bixin_load_device(self.client, *args, **kwargs)

    def sign_tx(self, *args, **kwargs):
        with self.run_flow():
            return trezor_btc.sign_tx(self.client, *args, **kwargs)

    def sign_eth_tx(self, *args, **kwargs):
        with self.run_flow():
            return trezor_ethereum.sign_tx(self.client, *args, **kwargs)

    def reset_device(self, *args, **kwargs):
        with self.run_flow():
            return trezor_device.reset(self.client, *args, **kwargs)

    def wipe_device(self, *args, **kwargs):
        with self.run_flow():
            return trezor_device.wipe(self.client, *args, **kwargs)

    # ========= UI methods ==========

    def button_request(self, code):
        message = self.msg or MESSAGES.get(code) or MESSAGES['default']
        self.handler.button_request(code)
        self.handler.show_message(message.format(self.device), self.client.cancel)

    def get_pin(self, code=None):
        show_strength = True
        if code == 2:
            if isinstance(self.handler, CustomerUI):
                msg = "2"
            else:
                msg = _("Enter a new PIN for your {}:")
        elif code == 3:
            if isinstance(self.handler, CustomerUI):
                msg = "3"
            else:
                msg = (_("Re-enter the new PIN for your {}.\n\n"
                         "NOTE: the positions of the numbers have changed!"))
        else:
            if isinstance(self.handler, CustomerUI):
                msg = "1"
            else:
                msg = _("Enter your current {} PIN:")
            show_strength = False
        pin = self.handler.get_pin(msg.format(self.device), show_strength=show_strength)
        if not pin:
            raise Cancelled
        if len(pin) < 1 and len(pin) != 18:
            self.handler.show_error(_('The PIN cannot be longer than 9 characters.'))
            raise Cancelled
        return pin

    def get_passphrase(self, available_on_device):
        if self.creating_wallet:
            if isinstance(self.handler, CustomerUI):
                msg = "6"
            else:
                msg = _("Enter a passphrase to generate this wallet.  Each time "
                        "you use this wallet your {} will prompt you for the "
                        "passphrase.  If you forget the passphrase you cannot "
                        "access the bitcoins in the wallet.").format(self.device)
        else:
            if isinstance(self.handler, CustomerUI):
                msg = "3"
            else:
                msg = _("Enter the passphrase to unlock this wallet:")

        self.handler.passphrase_on_device = available_on_device
        passphrase = self.handler.get_passphrase(msg, self.creating_wallet)
        if passphrase is PASSPHRASE_ON_DEVICE:
            return passphrase
        if passphrase is None:
            raise Cancelled
        passphrase = bip39_normalize_passphrase(passphrase)
        length = len(passphrase)
        if length > 50:
            self.handler.show_error(_("Too long passphrase ({} > 50 chars).").format(length))
            raise Cancelled
        return passphrase

    def _matrix_char(self, matrix_type):
        num = 9 if matrix_type == WordRequestType.Matrix9 else 6
        char = self.handler.get_matrix(num)
        if char == 'x':
            raise Cancelled
        return char

    def mnemonic_callback(self, recovery_type):
        if recovery_type is None:
            return None

        if recovery_type == RecoveryDeviceType.Matrix:
            return self._matrix_char

        step = 0

        def word_callback(_ignored):
            nonlocal step
            step += 1
            msg = _("Step {}/24.  Enter seed word as explained on your {}:").format(step, self.device)
            word = self.handler.get_word(msg)
            if not word:
                raise Cancelled
            return word

        return word_callback

    def reboot_to_bootloader(self) -> bool:
        """
        Reboot the device to bootloader mode if needed.
        :return: True if the device enters or is already in bootloader mode,
                 False otherwise.
        """
        if self.features.bootloader_mode:
            return True
        else:
            trezor_device.reboot(self.client)
            time.sleep(2)
            # this line would refresh features
            self.client.init_device()
            return self.features.bootloader_mode
