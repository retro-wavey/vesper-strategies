import brownie
from brownie import Contract
from helpers import stratData,vaultData


def test_operation(accounts, token, vault, strategy, strategist, amount, user, user2, want_pool, chain, gov, vsp):
    chain.snapshot()
    one_day = 86400
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) >= amount
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)

    # harvest 1: funds to strat
    strategy.harvest({"from": strategist})
    chain.mine(1)
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    assert strategy.estimatedTotalAssets()+1 >= amount
    
    # Harvest 2: Allow rewards to be earned
    print("\n**Harvest 2**")
    chain.sleep(one_day)
    chain.mine(1)
    strategy.harvest({"from": strategist})
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)

    print("\nEst APR: ", "{:.2%}".format(
            ((vault.totalAssets() - amount) * 365) / (amount)
        )
    )