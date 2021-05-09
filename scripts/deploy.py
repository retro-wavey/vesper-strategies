from pathlib import Path

from brownie import StrategyVesper, accounts, config, network, project, web3
from eth_utils import is_checksum_address
import click

API_VERSION = config["dependencies"][0].split("@")[-1]
Vault = project.load(
    Path.home() / ".brownie" / "packages" / config["dependencies"][0]
).Vault


def get_address(msg: str, default: str = None) -> str:
    val = click.prompt(msg, default=default)

    # Keep asking user for click.prompt until it passes
    while True:

        if is_checksum_address(val):
            return val
        elif addr := web3.ens.address(val):
            click.echo(f"Found ENS '{val}' [{addr}]")
            return addr

        click.echo(
            f"I'm sorry, but '{val}' is not a checksummed address or valid ENS record"
        )
        # NOTE: Only display default once
        val = click.prompt(msg)


def main():
    print(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    print(f"You are using: 'dev' [{dev.address}]")

    if input("Is there a Vault for this strategy already? y/[N]: ").lower() == "y":
        vault = Vault.at("0xA696a63cc78DfFa1a63E9E50587C197387FF6C7E")
        assert vault.apiVersion() == API_VERSION
    else:
        print("You should deploy one vault using scripts from Vault project")
        return  # TODO: Deploy one using scripts from Vault project

    print(
        f"""
    Strategy Parameters

       api: {API_VERSION}
     token: {vault.token()}
      name: '{vault.name()}'
    symbol: '{vault.symbol()}'
    """
    )
    publish_source = click.confirm("Verify source on etherscan?")
    if input("Deploy Strategy? y/[N]: ").lower() != "y":
        return

    strategy = StrategyVesper.deploy(
        vault, 
        "0x4B2e76EbBc9f2923d83F5FBDe695D8733db1a17B", # want pool
        "0x479A8666Ad530af3054209Db74F3C74eCd295f8D", # wbtc rewards
        "0x1b40183EFB4Dd766f11bDa7A7c3AD8982e998421", # vsp
        "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", # uniswap
        "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F", # sushiswap
        1e16, # min to sell
        False, # harvest pool profits
        {"from": dev},
        publish_source=publish_source
        )
