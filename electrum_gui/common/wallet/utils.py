import json

from electrum_gui.common.basic import exceptions as basic_exceptions


def decrypt_eth_keystore(keyfile_json: str, keystore_password: str) -> bytes:
    try:
        import eth_account

        return bytes(eth_account.account.Account.decrypt(keyfile_json, keystore_password))
    except (TypeError, KeyError, NotImplementedError, json.decoder.JSONDecodeError) as e:
        raise basic_exceptions.KeyStoreFormatError(other_info=str(e))
    except Exception as e:
        raise basic_exceptions.KeyStoreIncorrectPassword(other_info=str(e))
