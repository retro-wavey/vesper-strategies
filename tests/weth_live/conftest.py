import pytest
from brownie import config
from brownie import project
from brownie import Contract

from pathlib import Path
Vault = project.load(
    Path.home() / ".brownie" / "packages" / config["dependencies"][0]
).Vault

@pytest.fixture
def live_strategy():
    yield Contract("0xeE697232DF2226c9fB3F02a57062c4208f287851") # This one has 37% ratio

@pytest.fixture
def token():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH
    yield Contract(token_address)

@pytest.fixture
def whale(accounts):
    yield accounts.at("0x0F4ee9631f4be0a63756515141281A3E2B293Bbe", force=True)


@pytest.fixture
def user(accounts):
    yield accounts[6]

@pytest.fixture
def user2(accounts):
    yield accounts[7]

@pytest.fixture
def gov(accounts):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)   


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def management(accounts):
    yield accounts[3]


@pytest.fixture
def strategist(accounts):
    yield accounts[4]


@pytest.fixture
def keeper(accounts):
    yield accounts[5]


@pytest.fixture
def amount(accounts, token, user, user2, whale):
    amount = 10 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    token.transfer(user, amount, {"from": whale})
    yield amount


@pytest.fixture
def weth():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    yield Contract(token_address)


@pytest.fixture
def weth_amout(gov, weth):
    weth_amout = 10 ** weth.decimals()
    gov.transfer(weth, weth_amout)
    yield weth_amout

@pytest.fixture
def vsp(accounts, user):
    amount = 1e20
    token_address = "0x1b40183EFB4Dd766f11bDa7A7c3AD8982e998421"
    vspContract = Contract(token_address)
    reserve = accounts.at("0x9520b477Aa81180E6DdC006Fc09Fb6d3eb4e807A", force=True)
    vspContract.transfer(user, amount, {"from": reserve})
    yield vspContract

@pytest.fixture
def vault():
    yield Vault.at("0xa9fE4601811213c340e850ea305481afF02f5b28") # yvWETH

@pytest.fixture
def sushi_router():
   yield Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")

@pytest.fixture
def uni_router():
    yield Contract("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")

@pytest.fixture
def pool_rewards():
    yield Contract("0x93567318aaBd27E21c52F766d2844Fc6De9Dc738")

@pytest.fixture
def want_pool():
    yield Contract("0x103cc17C2B1586e5Cd9BaD308690bCd0BBe54D5e")


@pytest.fixture
def strategy(strategist, keeper, vault, live_strategy, StrategyVesper, gov, want_pool, pool_rewards, vsp, uni_router, sushi_router, chain):
    one_day = 86400
    strategy = strategist.deploy(
        StrategyVesper, 
        vault,
        want_pool,
        pool_rewards,
        vsp,
        uni_router,
        sushi_router,
        1e16,
        False
    )
    strategy.setKeeper(keeper)
    # Empty out another strat to make room
    vault.updateStrategyDebtRatio(live_strategy, 0, {"from": gov})
    live_strategy.harvest({"from": gov})
    chain.sleep(one_day)
    chain.mine(1)
    live_strategy.harvest({"from": gov})
    chain.sleep(one_day)
    chain.mine(1)
    live_strategy.harvest({"from": gov})

    chain.mine(1)
    vault.addStrategy(
        strategy, 
        1_500, 
        0, 
        2 ** 256 - 1,
        1_000, 
        {"from": gov}
    )
    
    yield strategy