import pytest
from brownie import config
from brownie import Contract


@pytest.fixture
def token():
    token_address = "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"  # WBTC
    yield Contract(token_address)
    
@pytest.fixture
def vToken():
    yield Contract("0x4B2e76EbBc9f2923d83F5FBDe695D8733db1a17B")

@pytest.fixture
def vault():
    yield Contract("0xA696a63cc78DfFa1a63E9E50587C197387FF6C7E") # new

@pytest.fixture
def live_strategy():
    yield Contract("0x53a65c8e238915c79a1e5C366Bc133162DBeE34f") # This one has 25% ratio

@pytest.fixture
def pool_rewards():
    yield Contract("0x479A8666Ad530af3054209Db74F3C74eCd295f8D")

@pytest.fixture
def whale(accounts):
    yield accounts.at("0xF977814e90dA44bFA03b6295A0616a897441aceC", force=True)

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
def amount(accounts, token, user, user2, whale, vault, gov):
    amount = 1 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    mega = 1000 * 10 ** token.decimals()
    token.transfer(user, amount, {"from": whale})
    #token.transfer(user2, mega, {"from": whale})
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
def sushi_router():
    yield Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")

@pytest.fixture
def uni_router():
    yield Contract("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")

@pytest.fixture
def want_pool(vToken):
    yield vToken


@pytest.fixture
def strategy(strategist, keeper, vault, live_strategy, StrategyVesper, gov, want_pool, pool_rewards, vsp, uni_router, sushi_router, chain):
    one_day = 86400
    strategy = strategist.deploy(
        StrategyVesper, 
        vault,
        want_pool,
        pool_rewards,
        1e16,
        0,
        5_000 # 50%
    )
    strategy.setKeeper(keeper)
    # Empty debtRatio from other strats to make room

    vault.updateStrategyDebtRatio(live_strategy, 0, {"from": gov})
    live_strategy.harvest({"from": gov})
    chain.mine(1)

    debt_ratio = 1_000                 # 98%
    minDebtPerHarvest = 0             # Lower limit on debt add
    maxDebtPerHarvest = 2 ** 256 - 1  # Upper limit on debt add
    performance_fee = 1000            # Strategist perf fee: 10%

    vault.addStrategy(
        strategy, 
        debt_ratio, 
        minDebtPerHarvest, 
        maxDebtPerHarvest, 
        performance_fee,
        {"from": gov}
    )
    
    yield strategy