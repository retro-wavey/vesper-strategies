import pytest
import brownie
from brownie import Wei, accounts, Contract, config


@pytest.mark.require_network("mainnet-fork")
def test_clone(StrategyVesper, 
    accounts, wbtc, usdc, usdc_vault, wbtc_vault, wbtc_strategy, pool_rewards_usdc, pool_rewards_wbtc, uni_router, sushi_router, strategist, amount_usdc,amount_wbtc, user, user2, want_pool_wbtc, want_pool_usdc, chain, gov, vsp
):
    one_day = 86400
    # Try a deposit and harvest
    before_bal = usdc.balanceOf(user)
    wbtc.approve(wbtc_vault, 2 ** 256 - 1, {"from": user})
    wbtc_vault.deposit(amount_wbtc,{"from": user})

    # Invest!
    wbtc_strategy.harvest({"from": strategist})
    chain.sleep(one_day)
    chain.mine()
    wbtc_strategy.harvest({"from": strategist})

    print("\nEst WBTC APR: ", "{:.2%}".format(
            ((wbtc_vault.totalAssets() - amount_wbtc) * 365) / (amount_wbtc)
        )
    )
    # Shouldn't be able to call initialize on WBTC again
    with brownie.reverts():
        wbtc_strategy.initialize(
            wbtc_vault,
            strategist,
            strategist,
            strategist,
            want_pool_wbtc,
            pool_rewards_wbtc,
            vsp,
            uni_router,
            sushi_router,
            1e16,
            False
        )

    # Clone the strategy
    tx = wbtc_strategy.cloneVesper(
        usdc_vault,
        strategist,
        strategist,
        strategist,
        want_pool_usdc,
        pool_rewards_usdc,
        vsp,
        uni_router,
        sushi_router,
        1e16,
        False
    )

    usdc_strategy = StrategyVesper.at(tx.return_value)

    # Shouldn't be able to clone a clone
    with brownie.reverts():
        tx = usdc_strategy.cloneVesper(
            usdc_vault,
            strategist,
            strategist,
            strategist,
            want_pool_usdc,
            pool_rewards_usdc,
            vsp,
            uni_router,
            sushi_router,
            1e16,
            False,{"from":gov}
        )

    # Shouldn't be able to call initialize again
    with brownie.reverts():
        usdc_strategy.initialize(
            usdc_vault,
            strategist,
            strategist,
            strategist,
            want_pool_usdc,
            pool_rewards_usdc,
            vsp,
            uni_router,
            sushi_router,
            1e16,
            False,
            {'from':gov}
        )

    usdc_vault.addStrategy(usdc_strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})

    # Try a deposit and harvest
    before_bal = usdc.balanceOf(user)
    usdc.approve(usdc_vault, 2 ** 256 - 1, {"from": user})
    usdc_vault.deposit(amount_usdc,{"from": user})

    # Invest!
    usdc_strategy.harvest({"from": strategist})

    # Wait one day
    chain.sleep(one_day)
    chain.mine()
    usdc_strategy.harvest({"from": strategist})
    print("\nEst USDC APR: ", "{:.2%}".format(
            ((usdc_vault.totalAssets() - amount_usdc) * 365) / (amount_usdc)
        )
    )

    # Get profits and withdraw
    usdc_vault.withdraw( 2**256 - 1, user, 61,{"from": user})
    assert before_bal * 0.94 < usdc.balanceOf(user)  # accounting for withdraw fee