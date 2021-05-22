import pytest
from brownie import config
from brownie import Contract

@pytest.fixture
def gov(accounts):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)

@pytest.fixture
def sushi_router():
    yield Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")

@pytest.fixture
def uni_router():
    yield Contract("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")

@pytest.fixture
def pool_rewards_wbtc():
    # yield Contract("0xd59996055b5E0d154f2851A030E207E0dF0343B0") # USDC
    # yield Contract("0x479A8666Ad530af3054209Db74F3C74eCd295f8D") # WBTC
    # yield Contract("0x93567318aaBd27E21c52F766d2844Fc6De9Dc738") # WETH
    yield Contract("0x514910771AF9Ca656af840dff83E8264EcF986CA") # LINK
    

@pytest.fixture
def pool_rewards_usdc():
    yield Contract("0xcA9AEeB14ff396F8661F7DF3128f88c31D2fDEC5") # LINK
    # yield Contract("0xd59996055b5E0d154f2851A030E207E0dF0343B0") # USDC
    # yield Contract("0x479A8666Ad530af3054209Db74F3C74eCd295f8D") # WBTC
    # yield Contract("0x93567318aaBd27E21c52F766d2844Fc6De9Dc738") # WETH

    
@pytest.fixture
def user(accounts):
    yield accounts[6]

@pytest.fixture
def user2(accounts):
    yield accounts[7]


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
def token():
    token_address = "0x514910771AF9Ca656af840dff83E8264EcF986CA"  # LINK
    yield Contract(token_address)

@pytest.fixture
def weth():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    yield Contract(token_address)


@pytest.fixture
def weth_amout(gov, weth, accounts):
    weth_amout = 10 ** weth.decimals()
    a = accounts[7]
    a.transfer(gov, "10 ether")
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
def whale(accounts):
    yield accounts.at("0xbe6977E08D4479C0A6777539Ae0e8fa27BE4e9d6", force=True)


@pytest.fixture
def amount(accounts, token, user, whale, vault, gov):
    amount = 1000 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    mega = 1000 * 10 ** token.decimals()
    token.transfer(user, amount, {"from": whale})
    #token.transfer(user2, mega, {"from": whale})
    yield amount

@pytest.fixture
def vault(pm, gov, token, rewards, guardian):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(gov, {"from": gov})
    yield vault

@pytest.fixture
def want_pool():
    yield Contract("0x0a27E910Aee974D05000e05eab8a4b8Ebd93D40C") # LINK

@pytest.fixture
def pool_rewards():
    yield Contract("0xcA9AEeB14ff396F8661F7DF3128f88c31D2fDEC5") # LINK

@pytest.fixture
def strategy(strategist, keeper, vault, StrategyVesper, gov, want_pool, pool_rewards, vsp, uni_router, sushi_router):
    one_day = 86400
    strategy = strategist.deploy(
        StrategyVesper, 
        vault,
        want_pool,
        pool_rewards,
        1e16,
        0,
        10_000, # 50% percent keep,
        "Vesper LINK"
    )
    strategy.setKeeper(keeper)
    # Empty debtRatio from other strats to make room

    debt_ratio = 10_000               # 100%
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
