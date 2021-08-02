import enum
import functools
from typing import Dict, Type

from electrum_gui.common.basic import bip44
from electrum_gui.common.coin import data
from electrum_gui.common.conf import chains as chains_conf
from electrum_gui.common.secret import data as secret_data

CHAINS_DICT = {}
COINS_DICT = {}


def _replace_enum_fields(raw_data: dict, fields: Dict[str, Type[enum.Enum]]):
    for field_name, enum_cls in fields.items():
        if field_name not in raw_data:
            continue

        enum_name = raw_data[field_name].upper()
        enum_ins = enum_cls[enum_name]
        raw_data[field_name] = enum_ins


def refresh_coins(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global COINS_DICT
        added_coins = chains_conf.get_added_coins(set(COINS_DICT.keys()))
        if added_coins:
            for coin in added_coins:
                coininfo = data.CoinInfo(**coin)
                COINS_DICT.setdefault(coininfo.code, coininfo)

        return func(*args, **kwargs)

    return wrapper


def refresh_chains(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global CHAINS_DICT
        for chain in chains_conf.get_added_chains(set(CHAINS_DICT.keys())):
            _replace_enum_fields(
                chain,
                {
                    "chain_model": data.ChainModel,
                    "curve": secret_data.CurveEnum,
                    "bip44_last_hardened_level": bip44.BIP44Level,
                    "bip44_auto_increment_level": bip44.BIP44Level,
                    "bip44_target_level": bip44.BIP44Level,
                },
            )
            chaininfo = data.ChainInfo(**chain)
            CHAINS_DICT.setdefault(chaininfo.chain_code, chaininfo)
        return func(*args, **kwargs)

    return wrapper
