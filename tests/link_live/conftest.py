import pytest
from brownie import config
from brownie import Contract


@pytest.fixture
def token():
    token_address = "0x514910771AF9Ca656af840dff83E8264EcF986CA"  # LINK
    yield Contract(token_address)
    
@pytest.fixture
def vToken():
    yield Contract("0x0a27E910Aee974D05000e05eab8a4b8Ebd93D40C")

@pytest.fixture
def vault():
    yield Contract("0xF962B098Ecc4352aA2AD1d4164BD2b8367fd94c3") # new

@pytest.fixture
def live_strategy():
    yield Contract("0x3aD22Fd9e2cc898d6F77AC12eAc603A77a464c45") # This one has 90% ratio

@pytest.fixture
def pool_rewards():
    yield Contract("0xcA9AEeB14ff396F8661F7DF3128f88c31D2fDEC5")

@pytest.fixture
def whale(accounts):
    yield accounts.at("0xbe6977E08D4479C0A6777539Ae0e8fa27BE4e9d6", force=True)

@pytest.fixture
def user(accounts):
    yield accounts[6]

@pytest.fixture
def user2(accounts):
    yield accounts[7]

@pytest.fixture
def gov(accounts):
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)  
    #yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)   


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
    yield "0x6AFB7c9a6E8F34a3E0eC6b734942a5589A84F44C"


@pytest.fixture
def keeper(accounts):
    yield accounts[5]

@pytest.fixture
def amount(accounts, token, user, user2, whale, vault, gov):
    amount = 100 * 10 ** token.decimals()
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
def strategy(strategist, accounts, keeper, vault, live_strategy, StrategyVesper, gov, want_pool, pool_rewards, vsp, uni_router, sushi_router, chain):
    one_day = 86400
    # strategy = strategist.deploy(
    #     StrategyVesper, 
    #     vault,
    #     want_pool,
    #     pool_rewards,
    #     1e16,
    #     0,
    #     5_000, # 50% percent keep,
    #     "Vesper LINK"
    # )
    # strategy.setKeeper(keeper)
    # Empty debtRatio from other strats to make room
    strategy = Contract("0xFB9030A52A420155D1266260271A0a8A23f4443A")
    sms = accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)
    aave_strat = "0xDb6DF092281718be78F41E7Fea328499dc6088D4"
    vault.updateStrategyDebtRatio(aave_strat, 7_000, {"from": sms})
    vault.addStrategy(
        strategy,       # new strat
        2_000,          # debtRatio
        0,              # min
        2 ** 256 - 1,   # max
        1000,           # perf fee
        {"from": sms}
    )
    
    yield strategy