import json
import logging
from typing import Optional

from trezorlib import customer_ui as trezorlib_customer_ui

from electrum import constants as electrum_constants
from electrum import keystore as electrum_keystore
from electrum import plugin as electrum_plugin
from electrum_gui.common.basic import api
from electrum_gui.common.hardware import manager as hardware_manager
from electrum_gui.common.hardware.callbacks import helper as hardware_agent_helper
from electrum_gui.common.provider import manager as provider_manager

TREZOR_PLUGIN_NAME = 'trezor'

logger = logging.getLogger("app.hardware")


class TrezorManager(object):
    """Interact with hardwares via electrum's trezor plugin."""

    exposed_commands = (
        'hardware_verify',
        'backup_wallet',
        'se_proxy',
        'bixin_backup_device',
        'bixin_load_device',
        'recovery_wallet_hw',
        'bx_inquire_whitelist',
        'bx_add_or_delete_whitelist',
        'apply_setting',
        'init',
        'reset_pin',
        'wipe_device',
        'get_passphrase_status',
        'get_feature',
        'firmware_update',
        'ensure_client',
    )

    def __init__(self, plugin_manager: electrum_plugin.Plugins) -> None:
        self.plugin = plugin_manager.get_plugin(TREZOR_PLUGIN_NAME)

    def ensure_legacy_plugin_client(self, path: str):
        """
        Fixme: Keep it until it is fully migrated
        Affected interface: sign_tx
        """
        self.plugin.get_client(path=path, ui=trezorlib_customer_ui.CustomerUI())

    def get_device_id(self, path: str, from_recovery=False) -> str:
        feature = hardware_manager.get_feature(hardware_device_path=path)
        return feature["serial_num"]

    def get_xpub(self, coin: str, path: str, derivation: str, _type: str, creating: bool, from_recovery=False) -> str:
        hardware_agent_helper.set_value_to_agent("is_creating_wallet", creating)
        return provider_manager.hardware_get_xpub(coin, path, derivation)

    def get_eth_xpub(self, coin, path: str, derivation: str, from_recovery=False) -> str:
        xpub = provider_manager.hardware_get_xpub(coin, path, derivation)

        if electrum_constants.net.TESTNET and xpub.startswith("xpub"):
            node = electrum_keystore.BIP32Node.from_xkey(xpub, net=electrum_constants.BitcoinMainnet)
            return node.to_xpub(net=electrum_constants.BitcoinTestnet)
        else:
            return xpub

    # === End helper methods used in console.AndroidCommands ===

    # Below are exposed methods, would be directly called from the upper users.

    @api.api_entry()
    def ensure_client(self, path: str) -> None:
        self.get_feature(path)  # ensure new way
        self.ensure_legacy_plugin_client(path)  # ensure old way

    @api.api_entry()
    def hardware_verify(self, msg: str, path: str = "android_usb") -> str:
        """
        Anti-counterfeiting verification, used by hardware
        :param msg: msg as str
        :param path: NFC/android_usb/bluetooth as str
        :return: json like
            {'serialno': 'Bixin20051500293',
             'is_bixinkey': 'True',
             'is_verified': 'True',
             'last_check_time': 1611904981}
        """
        result = hardware_manager.do_anti_counterfeiting_verification(path, msg)
        return json.dumps(result)

    @api.api_entry()
    def backup_wallet(self, path: str = "android_usb") -> str:
        """
        Deprecated

        Backup wallet by se
        :param path: NFC/android_usb/bluetooth as str, used by hardware
        :return:
        """
        raise NotImplementedError()

    def se_proxy(self, message: str, path: str = "android_usb") -> str:
        """
        Deprecated
        """
        raise NotImplementedError()

    @api.api_entry()
    def bixin_backup_device(self, path: str = "android_usb") -> str:
        """
        Export seed, used by hardware
        :param path: NFC/android_usb/bluetooth as str
        :return: as string
        """
        return hardware_manager.backup_mode__read_mnemonic_from_device(path)

    @api.api_entry()
    def bixin_load_device(
        self,
        path: str = "android_usb",
        mnemonics: Optional[str] = None,
        language: str = "english",
        label: str = "OneKey",
    ) -> bool:
        """
        Import seed, used by hardware
        :param path: NFC/android_usb/bluetooth as str
        :param mnemonics: as string
        :param language: used to set hardware language
        :param label:  used to set hardware label
        :return: raise except if error
        """
        return hardware_manager.backup_mode__write_mnemonic_to_device(
            path, mnemonic=mnemonics, language=language, label=label
        )

    @api.api_entry()
    def recovery_wallet_hw(self, path: str = "android_usb", *args) -> str:
        """
        Deprecated

        Recovery wallet by encryption
        :param path: NFC/android_usb/bluetooth as str, used by hardware
        :param args: encryption data as str
        :return:
        """

        raise NotImplementedError()

    @api.api_entry()
    def bx_inquire_whitelist(self, path: str = "android_usb", **kwargs) -> str:
        """
        Deprecated

        Inquire
        :param path: NFC/android_usb/bluetooth as str, used by hardware
        :param kwargs:
            type:2=inquire
            addr_in: addreess as str
        :return:
        """
        raise NotImplementedError()

    @api.api_entry()
    def bx_add_or_delete_whitelist(self, path: str = "android_usb", **kwargs) -> str:
        """
        Deprecated

        Add and delete whitelist
        :param path: NFC/android_usb/bluetooth as str, used by hardware
        :param kwargs:
            type:0=add 1=delete
            addr_in: addreess as str
        :return:
        """
        raise NotImplementedError()

    @api.api_entry()
    def apply_setting(self, path: str = "nfc", **kwargs) -> int:
        """
        Set the hardware function, used by hardware
        :param path: NFC/android_usb/bluetooth as str
        :param kwargs:
            label="wangls"
            language="chinese/english"
            use_passphrase=true/false
            auto_lock_delay_ms="600"
            use_ble=true/false
            use_se=true/false
            is_bixinapp=true/false
        :return:0/1
        """
        return 1 if hardware_manager.apply_settings(path, settings=kwargs) else 0

    @api.api_entry()
    def init(
        self,
        path: str = "android_usb",
        label: str = "OneKey",
        language: str = "english",
        stronger_mnemonic: Optional[str] = None,
        use_se: bool = False,
    ) -> int:
        """
        Activate the device, used by hardware
        :param stronger_mnemonic: if not None 256  else 128
        :param path: NFC/android_usb/bluetooth as str
        :param label: name as string
        :param language: as string
        :param use_se: as bool (deprecated)
        :return:0/1
        """
        return (
            1
            if hardware_manager.setup_mnemonic_on_device(
                path,
                language=language,
                label=label,
                mnemonic_strength=256 if stronger_mnemonic else 128,
            )
            else 0
        )

    @api.api_entry()
    def reset_pin(self, path: str = "android_usb") -> int:
        """
        Reset pin, used by hardware
        :param path:NFC/android_usb/bluetooth as str
        :return:0/1
        """
        return 1 if hardware_manager.setup_or_change_pin(path) else 0

    @api.api_entry()
    def wipe_device(self, path: str = "android_usb") -> int:
        """
        Reset device, used by hardware
        :param path: NFC/android_usb/bluetooth as str
        :return:0/1
        """
        return 1 if hardware_manager.wipe_device(path) else 0

    def get_passphrase_status(self, path: str = "android_usb") -> bool:
        feature = hardware_manager.get_feature(path)
        return feature.get("passphrase_protection", False)

    @api.api_entry()
    def get_feature(self, path: str = "android_usb") -> str:
        """
        Get hardware information, used by hardware
        :param path: NFC/android_usb/bluetooth as str
        :return: dict like:
            {capabilities: List[EnumTypeCapability] = None,
            vendor: str = None,
            major_version: int = None,  主版本号
            minor_version: int = None,  次版本号
            patch_version: int = None
                修订号，即硬件的软件版本(俗称固件，在2.0.1 之前使用)
            bootloader_mode: bool = None,  设备当前是不是在bootloader模式
            device_id: str = None,  设备唯一标识，设备恢复出厂设置这个值会变
            pin_protection: bool = None, 是否开启了PIN码保护，
            passphrase_protection: bool = None
                是否开启了passphrase功能，这个用来支持创建隐藏钱包
            language: str = None, 设备当前使用的语言类型
            label: str = None,  激活钱包时，使用的名字,会显示在硬件主屏幕上
            initialized: bool = None, 当前设备是否激活
            revision: bytes = None,
            bootloader_hash: bytes = None,
            imported: bool = None, 标识硬件是否是通过导入助记词激活的
            unlocked: bool = None,
            firmware_present: bool = None,
            needs_backup: bool = None,
            flags: int = None,
            model: str = None,
            fw_major: int = None,
            fw_minor: int = None,
            fw_patch: int = None,
            fw_vendor: str = None,
            fw_vendor_keys: bytes = None,
            unfinished_backup: bool = None,
            no_backup: bool = None,
            recovery_mode: bool = None,
            backup_type: EnumTypeBackupType = None,
            sd_card_present: bool = None,
            sd_protection: bool = None,
            wipe_code_protection: bool = None,
            session_id: bytes = None,
            passphrase_always_on_device: bool = None,
            safety_checks: EnumTypeSafetyCheckLevel = None,
            auto_lock_delay_ms: int = None, 自动关机时间
            display_rotation: int = None,
            experimental_features: bool = None,
            offset: int = None,  升级时断点续传使用的字段
            ble_name: str = None, 当前设备的蓝牙名字
            ble_ver: str = None,  当前设备的蓝牙固件版本
            ble_enable: bool = None, 当前设备蓝牙是否开启
            se_enable: bool = None, 当前设备的se芯片是否被使能
            se_ver: str = None,  当前设备的se的版本
            backup_only: bool = None
                当前设备是否是特殊设备，只用来备份，没有额外功能支持
            onekey_version: str = None
                设备的软件版本（俗称固件），仅供APP使用（从2.0.1开始加入）
            serial_num: str = None 硬件序列号  (从2.0.7开始加入，用来取代`device_id`作为硬件唯一标识)
            }
        """
        result = hardware_manager.get_feature(path, force_refresh=True)

        return json.dumps(result)

    @api.api_entry(force_version=api.Version.V2)
    def firmware_update(
        self,
        filename: str,
        path: str,
        type: str = "",
        fingerprint: Optional[str] = None,
        skip_check: bool = True,
        raw: bool = False,
        dry_run: bool = False,
    ) -> None:
        """
        Upload new firmware to device.used by hardware
        Note : Device must be in bootloader mode.
        :param filename: full path to local upgrade file
        :param path: NFC/android_usb/bluetooth as str
        :param fingerprint: use default
        :param skip_check: use default
        :param raw: if raw data passed
        :param dry_run: use default
        :param type: use to different nrf and stm32, "" means stm32
        :return: None
        """
        if type or fingerprint or not skip_check:
            raise NotImplementedError()

        hardware_manager.update_firmware(path, filename, is_raw_data_only=raw, dry_run=dry_run)
