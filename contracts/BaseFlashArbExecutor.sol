// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BaseFlashArbExecutor
 * @notice Production-grade Atomic Flash Loan Arbitrage Contract on Base Layer 2
 * @dev Borrows funds from Balancer v2 Vault (0% protocol fee),
 *      executes cross-DEX swaps between Uniswap v3, Aerodrome, and PancakeSwap,
 *      and repays the loan in a single atomic transaction.
 *
 * SAFETY GUARANTEE:
 * If the net profit does not exceed `minProfit`, the transaction REVERTS automatically.
 * Capital risk is physically ZERO because state changes never commit if unprofitable.
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

interface IUniswapV3SwapRouter {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
}

interface IAerodromeRouter {
    struct Route {
        address from;
        address to;
        bool stable;
        address factory;
    }
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        Route[] calldata routes,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

interface IBalancerVault {
    function flashLoan(
        address recipient,
        IERC20[] memory tokens,
        uint256[] memory amounts,
        bytes memory userData
    ) external;
}

interface IFlashLoanRecipient {
    function receiveFlashLoan(
        IERC20[] memory tokens,
        uint256[] memory amounts,
        uint256[] memory feeAmounts,
        bytes memory userData
    ) external;
}

contract BaseFlashArbExecutor is IFlashLoanRecipient {
    address public immutable owner;
    IBalancerVault public immutable balancerVault;

    // Default Router addresses on Base Network (ChainId 8453)
    address public constant BALANCER_VAULT_BASE = 0xBA12222222228d8Ba5359726c66236535c7e3261;
    address public constant UNISWAP_V3_ROUTER_BASE = 0x2626664c2603336E57B271c5C0b26F421741e481;
    address public constant AERODROME_ROUTER_BASE = 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43;
    address public constant PANCAKESWAP_ROUTER_BASE = 0x678Aa4bF4E210cf2166753e054d5b7c31cc7fa86;

    event ArbitrageExecuted(
        address indexed tokenBorrowed,
        uint256 amountBorrowed,
        uint256 netProfit,
        uint256 timestamp
    );

    event ProfitWithdrawn(address indexed token, uint256 amount, address indexed recipient);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call");
        _;
    }

    constructor() {
        owner = msg.sender;
        balancerVault = IBalancerVault(BALANCER_VAULT_BASE);
    }

    struct ArbParams {
        address tokenIn;        // e.g. USDC or WETH
        address tokenTarget;    // e.g. AERO, cbBTC, etc.
        uint256 loanAmount;     // Size of Flash Loan (e.g. 10,000 USDC)
        uint256 minProfit;      // Minimum net profit in tokenIn (e.g. 20 USDC)
        uint8 dexBuy;           // 0: UniV3, 1: Aero, 2: Pancake
        uint8 dexSell;          // 0: UniV3, 1: Aero, 2: Pancake
        uint24 uniBuyFee;       // Pool fee tier (e.g. 500 for 0.05%)
        uint24 uniSellFee;      // Pool fee tier
        bool aeroBuyStable;     // Aero route stable flag
        bool aeroSellStable;    // Aero route stable flag
    }

    /**
     * @notice Initiates the Flash Loan from Balancer Vault
     * @param params Packed parameters specifying the route, amount, and required profit
     */
    function executeArbitrage(ArbParams calldata params) external onlyOwner {
        IERC20[] memory tokens = new IERC20[](1);
        tokens[0] = IERC20(params.tokenIn);

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = params.loanAmount;

        bytes memory userData = abi.encode(params);
        balancerVault.flashLoan(address(this), tokens, amounts, userData);
    }

    /**
     * @notice Balancer Flash Loan callback. Executes both legs of the trade.
     * @dev Must repay `amounts[0] + feeAmounts[0]` to the Balancer Vault before finishing.
     */
    function receiveFlashLoan(
        IERC20[] memory tokens,
        uint256[] memory amounts,
        uint256[] memory feeAmounts,
        bytes memory userData
    ) external override {
        require(msg.sender == address(balancerVault), "Caller must be Balancer Vault");

        ArbParams memory params = abi.decode(userData, (ArbParams));
        IERC20 borrowedToken = tokens[0];
        uint256 loanAmount = amounts[0];
        uint256 fee = feeAmounts[0]; // Balancer fee is 0% on Base

        // Leg 1: BUY target token on cheaper DEX
        uint256 targetAmountBought = _executeSwap(
            params.dexBuy,
            params.tokenIn,
            params.tokenTarget,
            loanAmount,
            params.uniBuyFee,
            params.aeroBuyStable
        );
        require(targetAmountBought > 0, "Leg 1 swap returned 0 tokens");

        // Leg 2: SELL target token on more expensive DEX back to tokenIn
        uint256 returnAmount = _executeSwap(
            params.dexSell,
            params.tokenTarget,
            params.tokenIn,
            targetAmountBought,
            params.uniSellFee,
            params.aeroSellStable
        );

        // ATOMIC SAFETY AUDIT: Verify net profitability
        uint256 totalOwed = loanAmount + fee;
        require(returnAmount > totalOwed, "Arbitrage did not generate profit: REVERTING");

        uint256 netProfit = returnAmount - totalOwed;
        require(netProfit >= params.minProfit, "Net profit below minProfit threshold: REVERTING");

        // Repay Flash Loan principal + fee to Balancer Vault
        borrowedToken.transfer(address(balancerVault), totalOwed);

        emit ArbitrageExecuted(params.tokenIn, loanAmount, netProfit, block.timestamp);
    }

    /**
     * @dev Internal swap router dispatcher
     */
    function _executeSwap(
        uint8 dex,
        address fromToken,
        address toToken,
        uint256 amountIn,
        uint24 feeTier,
        bool aeroStable
    ) internal returns (uint256 amountOut) {
        if (dex == 0) {
            // Uniswap v3
            IERC20(fromToken).approve(UNISWAP_V3_ROUTER_BASE, amountIn);
            IUniswapV3SwapRouter router = IUniswapV3SwapRouter(UNISWAP_V3_ROUTER_BASE);
            IUniswapV3SwapRouter.ExactInputSingleParams memory p = IUniswapV3SwapRouter.ExactInputSingleParams({
                tokenIn: fromToken,
                tokenOut: toToken,
                fee: feeTier,
                recipient: address(this),
                amountIn: amountIn,
                amountOutMinimum: 0,
                sqrtPriceLimitX96: 0
            });
            return router.exactInputSingle(p);
        } else if (dex == 1) {
            // Aerodrome Finance
            IERC20(fromToken).approve(AERODROME_ROUTER_BASE, amountIn);
            IAerodromeRouter router = IAerodromeRouter(AERODROME_ROUTER_BASE);
            IAerodromeRouter.Route[] memory routes = new IAerodromeRouter.Route[](1);
            routes[0] = IAerodromeRouter.Route({
                from: fromToken,
                to: toToken,
                stable: aeroStable,
                factory: address(0) // Aerodrome router infers factory
            });
            uint256[] memory amounts = router.swapExactTokensForTokens(
                amountIn,
                0,
                routes,
                address(this),
                block.timestamp + 300
            );
            return amounts[amounts.length - 1];
        } else if (dex == 2) {
            // PancakeSwap v3
            IERC20(fromToken).approve(PANCAKESWAP_ROUTER_BASE, amountIn);
            IUniswapV3SwapRouter router = IUniswapV3SwapRouter(PANCAKESWAP_ROUTER_BASE);
            IUniswapV3SwapRouter.ExactInputSingleParams memory p = IUniswapV3SwapRouter.ExactInputSingleParams({
                tokenIn: fromToken,
                tokenOut: toToken,
                fee: feeTier,
                recipient: address(this),
                amountIn: amountIn,
                amountOutMinimum: 0,
                sqrtPriceLimitX96: 0
            });
            return router.exactInputSingle(p);
        } else {
            revert("Unsupported DEX identifier");
        }
    }

    /**
     * @notice Withdraws accumulated profits to owner
     */
    function withdraw(address token, uint256 amount) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        uint256 withdrawAmt = amount > bal ? bal : amount;
        require(withdrawAmt > 0, "No balance to withdraw");
        IERC20(token).transfer(owner, withdrawAmt);
        emit ProfitWithdrawn(token, withdrawAmt, owner);
    }

    /**
     * @notice Withdraws native ETH if any
     */
    function withdrawETH() external onlyOwner {
        uint256 bal = address(this).balance;
        require(bal > 0, "No ETH to withdraw");
        payable(owner).transfer(bal);
    }

    receive() external payable {}
}
