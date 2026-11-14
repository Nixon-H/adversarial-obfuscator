"""Deploy a minimal ERC-721 and mint a licence token for the chain gate.

Reads the deployer key from NIXON_DEPLOY_KEY (hex, with or without 0x).
Never accepts a key from argv, config files, or source code.
Compiles the contract from Solidity source via py-solc-x (same tool the
existing NixonLicense deployer uses) — no raw bytecode blobs.

Usage:
  export NIXON_DEPLOY_KEY=<funded private key hex>
  export NIXON_DEPLOY_OWNER=<customer address>
  # optional:
  export NIXON_DEPLOY_CHAIN=polygon   # or base, arbitrum, ethereum
  export NIXON_DEPLOY_RPC=<RPC URL>   # overrides the chain preset

  python3 scripts/deploy_erc721_licence.py

Output: the exact --chain line to pass to the licence issue command.
"""

import os
import sys

L2_PRESETS = {
    "polygon": {
        "rpc": "https://polygon-rpc.com",
        "chain_id": 137,
        "gas_token": "POL",
        "min_balance_wei": 10 ** 17,  # 0.1 POL is plenty
        "gas": 2_500_000,
        "note": "cheapest, every exchange lists POL",
    },
    "base": {
        "rpc": "https://mainnet.base.org",
        "chain_id": 8453,
        "gas_token": "ETH",
        "min_balance_wei": 10 ** 13,  # 0.00001 ETH
        "gas": 2_000_000,
        "note": "Coinbase-backed, ETH gas",
    },
    "arbitrum": {
        "rpc": "https://arb1.arbitrum.io/rpc",
        "chain_id": 42161,
        "gas_token": "ETH",
        "min_balance_wei": 10 ** 13,
        "gas": 2_500_000,
        "note": "strongest L2 security, ETH gas",
    },
    "ethereum": {
        "rpc": "https://ethereum-rpc.publicnode.com",
        "chain_id": 1,
        "gas_token": "ETH",
        "min_balance_wei": 5 * 10 ** 15,  # 0.005 ETH
        "gas": 2_500_000,
        "note": "mainnet, expensive gas",
    },
}

ERC721_SOURCE = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LicenceERC721 {
    string public name = "Nixon Licence";
    string public symbol = "NXL";
    address public owner;
    uint256 public nextTokenId = 1;
    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    /// The chain gate calls ownerOf(tokenId) via eth_call.
    function ownerOf(uint256 tokenId) public view returns (address) {
        address addr = _owners[tokenId];
        require(addr != address(0), "token does not exist");
        return addr;
    }

    function balanceOf(address tokenOwner) public view returns (uint256) {
        return _balances[tokenOwner];
    }

    /// Mint a licence token to a customer address (deployer only).
    function mint(address to, uint256 tokenId) public onlyOwner {
        require(_owners[tokenId] == address(0), "token already minted");
        _owners[tokenId] = to;
        _balances[to] += 1;
        emit Transfer(address(0), to, tokenId);
    }

    /// Revoke: burn the token — the artifact stops on the next run.
    function burn(uint256 tokenId) public {
        require(_owners[tokenId] == msg.sender, "not the token holder");
        delete _owners[tokenId];
        _balances[msg.sender] -= 1;
        emit Transfer(msg.sender, address(0), tokenId);
    }
}
"""


def main():
    key_hex = os.environ.get("NIXON_DEPLOY_KEY", "").strip()
    if not key_hex:
        print("ERROR: set NIXON_DEPLOY_KEY (funded deployer private key, hex)")
        sys.exit(1)
    if key_hex.startswith("0x"):
        key_hex = key_hex[2:]

    chain_name = os.environ.get("NIXON_DEPLOY_CHAIN", "polygon").strip().lower()
    if chain_name not in L2_PRESETS:
        print(f"ERROR: unknown chain {chain_name!r}; "
              f"options: {', '.join(L2_PRESETS)}")
        sys.exit(1)
    preset = L2_PRESETS[chain_name]

    rpc_url = os.environ.get("NIXON_DEPLOY_RPC", "").strip() or preset["rpc"]
    owner = os.environ.get("NIXON_DEPLOY_OWNER", "").strip()
    if not owner or not owner.startswith("0x") or len(owner) != 42:
        print("ERROR: set NIXON_DEPLOY_OWNER (customer address, 0x + 40 hex)")
        sys.exit(1)

    try:
        from web3 import Web3
    except ImportError:
        print("ERROR: pip install web3")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"ERROR: cannot connect to {rpc_url}")
        sys.exit(1)
    chain_id = w3.eth.chain_id
    print(f"Connected: {chain_name} (chain {chain_id}), RPC {rpc_url}")

    acct = w3.eth.account.from_key("0x" + key_hex)
    print(f"Deployer: {acct.address}")
    balance = w3.eth.get_balance(acct.address)
    token = preset["gas_token"]
    gas_token_name = w3.from_wei(balance, "ether")
    print(f"Balance:  {gas_token_name} {token}")
    if balance < preset["min_balance_wei"]:
        print(f"ERROR: balance too low. Fund the wallet with ~$1-3 worth "
              f"of {token} on {chain_name} network.")
        print(f"  Exchange withdrawal → your address, network = "
              f"{chain_name.title()}")
        sys.exit(1)

    try:
        import solcx
    except ImportError:
        print("ERROR: pip install py-solc-x")
        sys.exit(1)
    try:
        solcx.install_solc("0.8.20")
    except Exception:
        pass
    solcx.set_solc_version("0.8.20")
    compiled = solcx.compile_source(ERC721_SOURCE,
                                    output_values=["abi", "bin"],
                                    solc_version="0.8.20")
    contract_key = "<stdin>:LicenceERC721"
    if contract_key not in compiled:
        contract_key = list(compiled.keys())[0]
    bytecode = compiled[contract_key]["bin"]
    print(f"Compiled ERC-721 ({len(bytecode) // 2} bytes)")

    print(f"\nDeploying on {chain_name} (chain {chain_id}) — "
          f"gas ~{preset['note']}")
    confirm = input("Type DEPLOY to confirm: ").strip()
    if confirm != "DEPLOY":
        print("Aborted.")
        sys.exit(1)

    nonce = w3.eth.get_transaction_count(acct.address)
    tx = {
        "from": acct.address,
        "data": bytecode,
        "nonce": nonce,
        "gas": preset["gas"],
        "gasPrice": w3.eth.gas_price,
        "chainId": chain_id,
    }
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"TX: {tx_hash.hex()} — waiting for receipt...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
    if receipt.status != 1:
        print("ERROR: deployment reverted")
        sys.exit(1)
    contract = receipt.contractAddress
    print(f"ERC-721 deployed at: {contract}")

    # Mint token 1 to the customer: mint(address,uint256) selector 0x40c10f19
    mint_data = "0x40c10f19" + owner[2:].rjust(64, "0") + hex(1)[2:].rjust(64, "0")
    nonce2 = w3.eth.get_transaction_count(acct.address)
    tx2 = {
        "from": acct.address,
        "to": contract,
        "data": mint_data,
        "nonce": nonce2,
        "gas": 120_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": chain_id,
    }
    signed2 = acct.sign_transaction(tx2)
    tx_hash2 = w3.eth.send_raw_transaction(signed2.raw_transaction)
    receipt2 = w3.eth.wait_for_transaction_receipt(tx_hash2, timeout=300)
    if receipt2.status != 1:
        print("ERROR: mint reverted")
        sys.exit(1)
    print(f"Token 1 minted to {owner}")

    # Verify ownerOf matches
    result = w3.eth.call({"to": contract,
                          "data": "0x6352211e" + hex(1)[2:].rjust(64, "0")})
    onchain_owner = "0x" + result.hex()[-40:]
    print(f"ownerOf(1) = {onchain_owner}")
    assert onchain_owner.lower() == owner.lower(), "mint owner mismatch"

    print()
    print("=" * 70)
    print("Issue the licence with this chain line:")
    print()
    print(f"  --chain contract={contract} token-id=1 owner={owner} "
          f"chain-id={chain_id}")
    print("=" * 70)
    print()
    print("Revocation: transfer or burn token 1 — the artifact stops")
    print("on the next run (fail-closed chain gate).")
    print(f"The chain_id={chain_id} is signed into the licence, so the")
    print("artifact is locked to this chain.")


if __name__ == "__main__":
    main()
