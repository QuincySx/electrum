import peewee

from electrum_gui.common.basic.orm.models import AutoDateTimeField, BaseModel
from electrum_gui.common.wallet import data


class WalletModel(BaseModel):
    id = peewee.AutoField(primary_key=True)
    type = peewee.IntegerField(choices=data.WalletType.to_choices())
    name = peewee.CharField()
    chain_code = peewee.CharField()
    created_time = AutoDateTimeField()
    modified_time = AutoDateTimeField()

    def __str__(self):
        return f"id: {self.id}, type: {self.type}, name: {self.name}, chain_code: {self.chain_code}"


class AccountModel(BaseModel):
    id = peewee.AutoField(primary_key=True)
    wallet_id = peewee.IntegerField()
    chain_code = peewee.CharField()
    address = peewee.CharField()
    address_encoding = peewee.CharField(null=True)
    pubkey_id = peewee.IntegerField(null=True)
    bip44_path = peewee.CharField(null=True)
    created_time = AutoDateTimeField()
    modified_time = AutoDateTimeField()

    def __str__(self):
        return f"id: {self.id}, wallet_id: {self.wallet_id}, chain_code: {self.chain_code}, address: {self.address}"


class AssetModel(BaseModel):
    id = peewee.AutoField(primary_key=True)
    wallet_id = peewee.IntegerField()
    account_id = peewee.IntegerField()
    chain_code = peewee.CharField()
    coin_code = peewee.CharField()
    balance = peewee.DecimalField(default=0)
    is_visible = peewee.BooleanField(default=True)
    created_time = AutoDateTimeField()
    modified_time = AutoDateTimeField()

    class Meta:
        indexes = ((("account_id", "coin_code"), True),)

    def __str__(self):
        return (
            f"id: {self.id}, wallet_id: {self.wallet_id}, account_id: {self.account_id}, "
            f"coin_code: {self.coin_code}, balance: {self.balance}"
        )
