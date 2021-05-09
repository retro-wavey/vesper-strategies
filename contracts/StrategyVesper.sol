// SPDX-License-Identifier: AGPL-3.0
// Feel free to change the license, but this is what we use

// Feel free to change this version of Solidity. We support >=0.6.0 <0.7.0;
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

// These are the core Yearn libraries
import {
    BaseStrategy
} from "@yearnvaults/contracts/BaseStrategy.sol";
import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "@openzeppelin/contracts/math/Math.sol";

interface IPoolRewards {
    function claimReward(address) external;
    function claimable(address) external view returns (uint256);
    function pool() external view returns (address);
    function rewardPerToken() external view returns (uint256);
}

interface IVesperPool {
    function approveToken() external;
    function deposit(uint256) external;
    function withdraw(uint256) external;
    function balanceOf(address) external view returns (uint256);
    function totalSupply() external view returns (uint256);
    function totalValue() external view returns (uint256);
    function rewardPerToken() external view returns (uint256);
    function getPricePerShare() external view returns (uint256);
    function withdrawFee() external view returns (uint256);
}

interface IUniswapV2Router {
    function getAmountsOut(uint256 amountIn, address[] calldata path)
        external
        view
        returns (uint256[] memory amounts);
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

interface IName {
    function name() external view returns (string memory);
}

contract StrategyVesper is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    // Vesper contracts: https://docs.vesper.finance/vesper-grow-pools/vesper-grow/audits#vesper-pool-contracts
    // Vesper vault strategies: https://medium.com/vesperfinance/vesper-grow-strategies-today-and-tomorrow-8bd7b907ba5
    address public wantPool;
    address public poolRewards;
    address public vsp;
    address public uniRouter;
    address public sushiRouter;
    address public activeDex;
    uint256 public minToSell;
    bool public harvestPoolProfits;
    bool public isOriginal = true;

    address public constant weth =          address(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);
    uint256 public constant DENOMINATOR =   1e30;

    constructor(
        address _vault,
        address _wantPool,
        address _poolRewards,
        address _vsp,
        address _uniRouter,
        address _sushiRouter,
        uint256 _minToSell,
        bool _harvestPoolProfits
    ) public BaseStrategy(_vault) {
        _initializeThis(
            _wantPool,
            _poolRewards,
            _vsp,
            _uniRouter,
            _sushiRouter,
            _minToSell,
            _harvestPoolProfits
        );
    }

    function _initializeThis(
        address _wantPool,
        address _poolRewards,
        address _vsp,
        address _uniRouter,
        address _sushiRouter,
        uint256 _minToSell,
        bool _harvestPoolProfits
    ) internal {
        require(
            address(wantPool) == address(0),
            "VesperStrategy already initialized"
        );

        wantPool = _wantPool;
        poolRewards = _poolRewards;
        vsp = _vsp;
        uniRouter = _uniRouter;
        sushiRouter = _sushiRouter;
        activeDex = _sushiRouter;
        minToSell = _minToSell;
        harvestPoolProfits = _harvestPoolProfits;
        
        IERC20(vsp).approve(sushiRouter, uint256(-1));
        IERC20(vsp).approve(uniRouter, uint256(-1));
        IERC20(want).approve(_wantPool, uint256(-1));
    }
    
    function _initialize(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _wantPool,
        address _poolRewards,
        address _vsp,
        address _uniRouter,
        address _sushiRouter,
        uint256 _minToSell,
        bool _harvestPoolProfits
    ) internal {
        // Parent initialize contains the double initialize check
        super._initialize(_vault, _strategist, _rewards, _keeper);
        _initializeThis(
            _wantPool,
            _poolRewards,
            _vsp,
            _uniRouter,
            _sushiRouter,
            _minToSell,
            _harvestPoolProfits
        );
    }

    function initialize(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _wantPool,
        address _poolRewards,
        address _vsp,
        address _uniRouter,
        address _sushiRouter,
        uint256 _minToSell,
        bool _harvestPoolProfits
    ) external {
        _initialize(
            _vault,
            _strategist,
            _rewards,
            _keeper,
            _wantPool,
            _poolRewards,
            _vsp,
            _uniRouter,
            _sushiRouter,
            _minToSell,
            _harvestPoolProfits
        );
    }

    function cloneVesper(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _wantPool,
        address _poolRewards,
        address _vsp,
        address _uniRouter,
        address _sushiRouter,
        uint256 _minToSell,
        bool _harvestPoolProfits
    ) external returns (address newStrategy) {
        require(isOriginal, "Clone inception!");
        // Copied from https://github.com/optionality/clone-factory/blob/master/contracts/CloneFactory.sol
        bytes20 addressBytes = bytes20(address(this));
        assembly {
            // EIP-1167 bytecode
            let clone_code := mload(0x40)
            mstore(
                clone_code,
                0x3d602d80600a3d3981f3363d3d373d3d3d363d73000000000000000000000000
            )
            mstore(add(clone_code, 0x14), addressBytes)
            mstore(
                add(clone_code, 0x28),
                0x5af43d82803e903d91602b57fd5bf30000000000000000000000000000000000
            )
            newStrategy := create(0, clone_code, 0x37)
        }

        StrategyVesper(newStrategy).initialize(
            _vault,
            _strategist,
            _rewards,
            _keeper,
            _wantPool,
            _poolRewards,
            _vsp,
            _uniRouter,
            _sushiRouter,
            _minToSell,
            _harvestPoolProfits
        );
    }

    function name() external view override returns (string memory) {
        return
            string(
                abi.encodePacked("Vesper ", IName(address(want)).name())
            );
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        uint256 totalWant = 0;

        // Calculate VSP holdings
        uint256 totalVSP = IERC20(vsp).balanceOf(address(this));
        totalVSP = totalVSP.add(IPoolRewards(poolRewards).claimable(address(this)));
        if(totalVSP > 0){
            totalWant = totalWant.add(convertVspToWant(totalVSP));
        }
        
        // Calculate want
        totalWant = totalWant.add(want.balanceOf(address(this)));
        return totalWant.add(calcWantHeldInVesper());
    }

    function calcWantHeldInVesper() internal view returns (uint256 wantBalance) {
        wantBalance = 0;
        uint256 shares = IVesperPool(wantPool).balanceOf(address(this));
        if(shares > 0){
            uint256 pps = morePrecisePricePerShare();
            uint256 withdrawableWant = convertTo18(pps.mul(shares)).div(DENOMINATOR);
            wantBalance = wantBalance.add(convertFrom18(withdrawableWant)); 
        }
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        
        _debtPayment = _debtOutstanding; // default is to pay the full debt

        // Here we begin doing stuff to make our profits
        uint256 claimable = IPoolRewards(poolRewards).claimable(address(this));
        if(claimable > 0){
            IPoolRewards(poolRewards).claimReward(address(this));
        }
        uint256 vspBal = IERC20(vsp).balanceOf(address(this));
        if(vspBal > minToSell){
            _sell(vspBal);
        }

        uint256 wantBalance = want.balanceOf(address(this));
        uint256 inVesper = calcWantHeldInVesper();
        uint256 assets = inVesper.add(wantBalance);
        uint256 debt = vault.strategies(address(this)).totalDebt;
        
        if(debt < assets){
            // Check whether we should "unhide" profits either because strategist/gov
            // says so, or because vault is trying to get all it's debt back 
            // (e.g. debtRatio was set to 0).
            if(harvestPoolProfits || _debtOutstanding >= debt){
                _profit = assets.sub(debt);
            }
            else{
                if(debt <= inVesper){
                    // Here we ignore pool profits and only count
                    // profits from VSP farming. This is intentional and is done
                    // to help make harvests much cheaper.
                    // as we won't have to free up pool profits
                    // each time and suffer the Vesper withdrawalFee. 
                    // Pool APR is very small compared to VSP rewards.
                    _profit = wantBalance;
                }
                else{ 
                    // Edge case where we've lost small money in the pool, 
                    // but at overall profit when rewards are added. Here we
                    // effectively only recognize partial amount of thhe rewards as 
                    // profit and leave the rest available to re-invest or pay debt.
                    _profit = assets.sub(debt);
                }
            }
        }
        else{ // This is bad, would imply strategy is net negative
            _loss = debt.sub(assets);
        }

        // We want to free up enough to pay profits + debt
        uint256 toFree = _debtOutstanding.add(_profit);

        if(toFree > wantBalance){
            toFree = toFree.sub(wantBalance);

            (uint256 liquidatedAmount, uint256 withdrawalLoss) = withdrawSome(toFree);
            wantBalance = wantBalance.add(liquidatedAmount);

            if(withdrawalLoss < _profit){
                _profit = _profit.sub(withdrawalLoss);
                _debtPayment = wantBalance.sub(_profit);
            }
            else{
                _loss = _loss.add(withdrawalLoss.sub(_profit));
                _profit = 0;
                _debtPayment = want.balanceOf(address(this));
            }
        }
    }

    function withdrawSome(uint256 _amount) internal returns (uint256 _liquidatedAmount, uint256 _loss) {
        uint256 wantBalanceBefore = want.balanceOf(address(this));
        uint256 vaultBalance = IERC20(wantPool).balanceOf(address(this)); // Vesper pool shares
        
        if(vaultBalance > 1){ // 1 not 0 because of possible rounding errors
            // Convert amount to Vesper shares.
            uint256 sharesToWithdraw = _amount
                    .mul(DENOMINATOR)
                    .div(morePrecisePricePerShare());
            sharesToWithdraw = Math.min(sharesToWithdraw, vaultBalance);
            IVesperPool(wantPool).withdraw(sharesToWithdraw);
        }

        uint256 withdrawnAmount = want.balanceOf(address(this)).sub(wantBalanceBefore);
        if(withdrawnAmount >= _amount){
            _liquidatedAmount = _amount;
        }
        else{
            _liquidatedAmount = withdrawnAmount;
            _loss = _amount.sub(withdrawnAmount);
        }
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        if (emergencyExit) {
            return;
        }
        
        uint256 wantBal = want.balanceOf(address(this));

        // In case we need to return want to the vault
        if (_debtOutstanding > wantBal) {
            return;
        }

        // Invest available want
        uint256 _wantAvailable = wantBal.sub(_debtOutstanding);
        if (_wantAvailable > 0) {
            IVesperPool(wantPool).deposit(_wantAvailable);
        }
    }

    function liquidatePosition(uint256 _amountNeeded) internal override returns (uint256 _liquidatedAmount, uint256 _loss) {

        uint256 wantBal = want.balanceOf(address(this));

        if (_amountNeeded > wantBal) {
            // Need more want to meet request.
            (, _loss) = withdrawSome(_amountNeeded.sub(wantBal));
        }
        _liquidatedAmount = Math.min(_amountNeeded, want.balanceOf(address(this)));
    }

    function _sell(uint256 _amount) internal {
        bool is_weth = address(want) == weth;
        address[] memory path = new address[](is_weth ? 2 : 3);
        path[0] = address(vsp);
        path[1] = weth;
        if (!is_weth) {
            path[2] = address(want);
        }
        IUniswapV2Router(activeDex)
            .swapExactTokensForTokens(_amount, 
                0, 
                path, 
                address(this), 
            now);
    }

    function prepareMigration(address _newStrategy) internal override {
        // Send all token balances to new strategy.
        // Want is taken care of in baseStrategy.
        // Intentionally not claiming rewards here to minimize chances 
        // that this function reverts.
        uint256 vTokenBalance = IERC20(wantPool).balanceOf(address(this));
        uint256 vspBalance = IERC20(vsp).balanceOf(address(this));

        if(vTokenBalance > 0){
            IERC20(wantPool).transfer(_newStrategy, vTokenBalance);
        }
        if(vspBalance > 0){
            IERC20(vsp).transfer(_newStrategy, vspBalance);
        }
    }
    
    function convertVspToWant(uint256 _amount) internal view returns (uint256) {
        bool is_weth = address(want) == weth;
        address[] memory path = new address[](is_weth ? 2 : 3);
        path[0] = address(vsp);
        if (is_weth) {
            path[1] = weth;
        } else {
            path[1] = weth;
            path[2] = address(want);
        }
        return IUniswapV2Router(activeDex).getAmountsOut(_amount, path)[path.length - 1];
    }

    function convertFrom18(uint256 _value) public view returns (uint256) {
        uint vaultDecimals = vault.decimals();
        if (vaultDecimals == 18) {
            return _value;
        }
        uint diff = 18 - vaultDecimals;
        return _value.div(10**diff);
    }

    function convertTo18(uint256 _value) public view returns (uint256) {
        uint vaultDecimals = vault.decimals();
        if (vaultDecimals == 18) {
            return _value;
        }
        uint diff = 18 - vault.decimals();
        return _value.mul(10**diff);
    }

    function toggleActiveDex() external onlyAuthorized {
        if(activeDex == sushiRouter){
            activeDex = uniRouter;
        }
        else{
            activeDex = sushiRouter;
        }
    }

    function toggleHarvestPoolProfits() external onlyAuthorized {
        harvestPoolProfits = !harvestPoolProfits;
    }

    function setMinToSell(uint256 _minToSell) external onlyAuthorized {
        require(_minToSell < 1e20, "!tooBig");
        require(_minToSell > 1e14, "!tooSmall");
        minToSell = _minToSell;
    }

    function protectedTokens() internal view override returns (address[] memory) {
        address[] memory protected = new address[](2);
        protected[0] = vsp;
        protected[1] = wantPool;
        return protected;
    }

    function morePrecisePricePerShare() public view returns (uint256) {
        // We do this because Vesper's contract gives us a not-very-precise pps
        return IVesperPool(wantPool)
            .totalValue().mul(DENOMINATOR) // denominated 1e8
            .div(IVesperPool(wantPool).totalSupply());
    }
}