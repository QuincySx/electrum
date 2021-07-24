# pyre-strict
import typing
from dataclasses import dataclass

from electrum_gui.common.provider.chains.stc.sdk import bcs
from electrum_gui.common.provider.chains.stc.sdk import serde_types as st
from electrum_gui.common.provider.chains.stc.sdk import starcoin_types
from electrum_gui.common.provider.chains.stc.sdk.starcoin_types import (
    AccountAddress,
    Identifier,
    ModuleId,
    ScriptFunction,
    TransactionPayload,
    TransactionPayload__ScriptFunction,
    TypeTag,
)


class ScriptFunctionCall:
    """Structured representation of a call into a known Move script function."""

    pass


@dataclass(frozen=True)
class ScriptFunctionCall__AcceptToken(ScriptFunctionCall):
    """."""

    token_type: starcoin_types.TypeTag


@dataclass(frozen=True)
class ScriptFunctionCall__PeerToPeer(ScriptFunctionCall):
    """."""

    token_type: starcoin_types.TypeTag
    payee: starcoin_types.AccountAddress
    payee_auth_key: bytes
    amount: st.uint128


@dataclass(frozen=True)
class ScriptFunctionCall__PeerToPeerV2(ScriptFunctionCall):
    """."""

    token_type: starcoin_types.TypeTag
    payee: starcoin_types.AccountAddress
    amount: st.uint128


def decode_script_function_payload(payload: TransactionPayload) -> ScriptFunctionCall:
    """Try to recognize a Diem `TransactionPayload` and convert it into a structured object `ScriptFunctionCall`."""
    if not isinstance(payload, TransactionPayload__ScriptFunction):
        raise ValueError("Unexpected transaction payload")
    script = payload.value
    helper = SCRIPT_FUNCTION_DECODER_MAP.get(script.module.name.value + script.function.value)
    if helper is None:
        raise ValueError("Unknown script bytecode")
    return helper(script)


def encode_accept_token_script_function(token_type: TypeTag) -> TransactionPayload:
    """."""
    return TransactionPayload__ScriptFunction(
        value=ScriptFunction(
            module=ModuleId(
                address=AccountAddress.from_hex("00000000000000000000000000000001"), name=Identifier("Account")
            ),
            function=Identifier("accept_token"),
            ty_args=[token_type],
            args=[],
        )
    )


def encode_peer_to_peer_v2_script_function(
    token_type: TypeTag, payee: AccountAddress, amount: st.uint128
) -> TransactionPayload:
    return TransactionPayload__ScriptFunction(
        value=ScriptFunction(
            module=ModuleId(
                address=AccountAddress.from_hex("00000000000000000000000000000001"), name=Identifier("TransferScripts")
            ),
            function=Identifier("peer_to_peer_v2"),
            ty_args=[token_type],
            args=[bcs.serialize(payee, starcoin_types.AccountAddress), bcs.serialize(amount, st.uint128)],
        )
    )


def decode_accept_token_script_function(script: TransactionPayload) -> ScriptFunctionCall:
    if not isinstance(script, ScriptFunction):
        raise ValueError("Unexpected transaction payload")
    return ScriptFunctionCall__AcceptToken(
        token_type=script.ty_args[0],
    )


def decode_peer_to_peer_script_function(script: TransactionPayload) -> ScriptFunctionCall:
    if not isinstance(script, ScriptFunction):
        raise ValueError("Unexpected transaction payload")
    return ScriptFunctionCall__PeerToPeer(
        token_type=script.ty_args[0],
        payee=bcs.deserialize(script.args[0], starcoin_types.AccountAddress),
        payee_auth_key=bcs.deserialize(script.args[1], bytes),
        amount=bcs.deserialize(script.args[2], st.uint128),
    )


def decode_peer_to_peer_v2_script_function(script: TransactionPayload) -> ScriptFunctionCall:
    if not isinstance(script, ScriptFunction):
        raise ValueError("Unexpected transaction payload")
    return ScriptFunctionCall__PeerToPeerV2(
        token_type=script.ty_args[0],
        payee=bcs.deserialize(script.args[0], starcoin_types.AccountAddress),
        amount=bcs.deserialize(script.args[1], st.uint128),
    )


SCRIPT_FUNCTION_DECODER_MAP: typing.Dict[str, typing.Callable[[TransactionPayload], ScriptFunctionCall]] = {
    "Accountaccept_token": decode_accept_token_script_function,
    "TransferScriptspeer_to_peer": decode_peer_to_peer_script_function,
    "TransferScriptspeer_to_peer_v2": decode_peer_to_peer_v2_script_function,
}
