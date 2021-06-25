import decimal
from unittest import TestCase
from unittest.mock import Mock, call, patch

from electrum_gui.common.price import data
from electrum_gui.common.price.channels.uniswap import Uniswap
from electrum_gui.common.provider.chains.eth.clients import geth as geth_client


class TestUniswap(TestCase):
    def setUp(self) -> None:
        self.uniswap = Uniswap()

    @patch("electrum_gui.common.conf.chains.get_uniswap_configs")
    @patch("electrum_gui.common.price.channels.uniswap.coin_manager")
    @patch("electrum_gui.common.price.channels.uniswap.provider_manager")
    def test_pricing(self, fake_provider_manager, fake_coin_manager, fake_get_uniswap_configs):
        mapping = {
            "eth": {
                "router_address": "0x_fake_router_address",
                "base_token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "media_token_addresses": [
                    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
                    "0xdac17f958d2ee523a2206206994597c13d831ec7",
                    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                    "0x6b175474e89094c44da98b954eedeac495271d0f",
                ],
            },
        }
        fake_get_uniswap_configs.side_effect = lambda chain_code: mapping.get(chain_code)
        fake_coin_manager.get_coin_info.return_value = Mock(chain_code="eth", code="eth", decimals=18)

        fake_client = Mock()
        fake_client.call_contract.return_value = [
            "0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000de0b6b3a76400000000000000000000000000000000000000000000000000000023d0b80e9cd0ea",
            "0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000de0b6b3a76400000000000000000000000000000000000000000000000000000000000000011a8000000000000000000000000000000000000000000000000000230ab0ee37b1cb",
            "0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000de0b6b3a76400000000000000000000000000000000000000000000000000000000000001b3411d00000000000000000000000000000000000000000000000000239130551746c4",
            "0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000de0b6b3a76400000000000000000000000000000000000000000000000000000000000001abdb3600000000000000000000000000000000000000000000000000230701312f17c1",
            "0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000de0b6b3a764000000000000000000000000000000000000000000000000000187f6610bc04af8bb00000000000000000000000000000000000000000000000000234e481a769f17",
            "0x0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000f424000000000000000000000000000000000000000000000000000013f33ca2bced9",
        ]
        fake_provider_manager.get_client_by_chain.return_value = fake_client

        self.assertEqual(
            [
                data.YieldedPrice(coin_code="eth_uni", price=decimal.Decimal("0.010081113122590954"), unit="eth"),
                data.YieldedPrice(coin_code="eth_usdt", price=decimal.Decimal("0.000350966644461273"), unit="eth"),
            ],
            list(
                self.uniswap.pricing(
                    [
                        Mock(
                            chain_code="eth",
                            code="eth_uni",
                            decimals=18,
                            token_address="0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
                        ),
                        Mock(
                            chain_code="eth",
                            code="eth_usdt",
                            decimals=6,
                            token_address="0xdac17f958d2ee523a2206206994597c13d831ec7",
                        ),
                        Mock(
                            chain_code="bsc",
                            code="bsc_cc",
                            decimals=18,
                            token_address="0x000000000000000000000000004597c13d831ec7",
                        ),
                    ]
                )
            ),
        )

        fake_get_uniswap_configs.assert_has_calls([call("bsc"), call("eth")])
        self.assertEqual(2, fake_get_uniswap_configs.call_count)
        fake_coin_manager.get_coin_info.assert_called_once_with("eth")

        fake_provider_manager.get_client_by_chain.assert_called_once_with("eth", instance_required=geth_client.Geth)
        fake_client.call_contract.assert_called_once_with(
            "0x_fake_router_address",
            [
                "0xd06ca61f0000000000000000000000000000000000000000000000000de0b6b3a7640000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000020000000000000000000000001f9840a85d5af5bf1d1762f925bdaddc4201f984000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "0xd06ca61f0000000000000000000000000000000000000000000000000de0b6b3a7640000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000030000000000000000000000001f9840a85d5af5bf1d1762f925bdaddc4201f9840000000000000000000000002260fac5e5542a773aa44fbcfedf7c193bc2c599000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "0xd06ca61f0000000000000000000000000000000000000000000000000de0b6b3a7640000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000030000000000000000000000001f9840a85d5af5bf1d1762f925bdaddc4201f984000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "0xd06ca61f0000000000000000000000000000000000000000000000000de0b6b3a7640000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000030000000000000000000000001f9840a85d5af5bf1d1762f925bdaddc4201f984000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "0xd06ca61f0000000000000000000000000000000000000000000000000de0b6b3a7640000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000030000000000000000000000001f9840a85d5af5bf1d1762f925bdaddc4201f9840000000000000000000000006b175474e89094c44da98b954eedeac495271d0f000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "0xd06ca61f00000000000000000000000000000000000000000000000000000000000f424000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000002000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
            ],
        )
