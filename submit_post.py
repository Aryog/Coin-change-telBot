import hashlib
import json

import requests
from typing import Optional, Dict, Any, List, Union
from pprint import pprint
import sys

from typing import Tuple, Optional
import binascii
from bip32 import BIP32, base58
from mnemonic import Mnemonic
from coincurve import PrivateKey

import hashlib
from typing import Optional
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_der

import time
from requests.exceptions import RequestException

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DeSoKeyPair:
    def __init__(self, public_key: bytes, private_key: bytes):
        self.public_key = public_key
        self.private_key = private_key


def create_key_pair_from_seed_or_seed_hex(
    seed: str,
    passphrase: str,
    index: int,
    is_testnet: bool
) -> Tuple[Optional[DeSoKeyPair], Optional[str]]:
    if not seed:
        return None, "Seed must be provided"

    # First try to decode as hex to determine if it's a seed hex
    try:
        seed_bytes = binascii.unhexlify(seed.lower())
        # If we get here, it's a valid hex string
        if passphrase or index != 0:
            return None, "Seed hex provided, but passphrase or index params were also provided"

        # Convert the seed hex directly to keys
        privkey = PrivateKey(seed_bytes)
        pubkey = privkey.public_key
        return DeSoKeyPair(pubkey.format(), privkey.secret), None

    except binascii.Error:
        # Not a valid hex string, treat as mnemonic
        try:
            # Validate and convert mnemonic to seed
            mnemo = Mnemonic("english")
            if not mnemo.check(seed):
                return None, "Invalid mnemonic seed phrase"

            seed_bytes = mnemo.to_seed(seed, passphrase)

            # Initialize BIP32 with appropriate network
            network = "test" if is_testnet else "main"
            bip32 = BIP32.from_seed(seed_bytes, network=network)

            # Derive the key path: m/44'/0'/index'/0/0
            # Note: in BIP32, hardened keys are represented with index + 0x80000000
            path = f"m/44'/0'/{index}'/0/0"
            derived_key = bip32.get_privkey_from_path(path)

            # Convert to coincurve keys for consistent interface
            privkey = PrivateKey(derived_key)
            pubkey = privkey.public_key

            return DeSoKeyPair(pubkey.format(), privkey.secret), None

        except Exception as e:
            return None, f"Error converting seed to key pair: {str(e)}"


def pubkey_to_base58(pubkey_bytes: bytes, is_testnet: bool) -> str:
    version_byte = b'\xcd' if is_testnet else b'\x19'
    payload = version_byte + pubkey_bytes
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return base58.b58encode(payload + checksum).decode('utf-8')


class DeSoDexClient:
    def __init__(self, is_testnet: bool = False, seed_phrase_or_hex=None, passphrase=None, index=0, node_url=None):
        self.is_testnet = is_testnet

        desoKeyPair, err = create_key_pair_from_seed_or_seed_hex(
            seed_phrase_or_hex, passphrase, index, is_testnet,
        )
        if desoKeyPair is None:
            raise ValueError(err)
        self.deso_keypair = desoKeyPair
        self.public_key_base58 = pubkey_to_base58(
            desoKeyPair.public_key, is_testnet)

        if node_url is None:
            self.node_url = "https://test.deso.org" if is_testnet else "https://node.deso.org"
        else:
            self.node_url = node_url.rstrip("/")

    def submit_post(
            self,
            updater_public_key_base58check: str,
            body: str,
            parent_post_hash_hex: Optional[str] = None,
            reposted_post_hash_hex: Optional[str] = None,
            title: Optional[str] = "",
            image_urls: Optional[List[str]] = None,
            video_urls: Optional[List[str]] = None,
            post_extra_data: Optional[Dict[str, Any]] = None,
            min_fee_rate_nanos_per_kb: int = 1000,
            is_hidden: bool = False,
            in_tutorial: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a post or repost to the DeSo blockchain.

        Args:
            updater_public_key_base58check: Public key of the updater.
            body: The content of the post.
            parent_post_hash_hex: The hash of the parent post for replies.
            reposted_post_hash_hex: The hash of the post being reposted.
            title: An optional title for the post.
            image_urls: Optional list of image URLs.
            video_urls: Optional list of video URLs.
            post_extra_data: Optional additional data for the post.
            min_fee_rate_nanos_per_kb: Minimum fee rate in nanos per KB.
            is_hidden: Boolean to indicate if the post is hidden.
            in_tutorial: Boolean to indicate if the post is part of a tutorial.

        Returns:
            Dict[str, Any]: Response from the DeSo node.

        Raises:
            ValueError: If the request fails.
        """
        url = f"{self.node_url}/api/v0/submit-post"
        payload = {
            "UpdaterPublicKeyBase58Check": updater_public_key_base58check,
            "PostHashHexToModify": "",
            "ParentStakeID": parent_post_hash_hex or "",
            "RepostedPostHashHex": reposted_post_hash_hex or "",
            "Title": title or "",
            "BodyObj": {
                "Body": body,
                "ImageURLs": image_urls or [],
                "VideoURLs": video_urls or [],
            },
            "PostExtraData": post_extra_data or {"Node": "1"},
            "Sub": "",
            "IsHidden": is_hidden,
            "MinFeeRateNanosPerKB": min_fee_rate_nanos_per_kb,
            "InTutorial": in_tutorial,
        }

        headers = {
            "Content-Type": "application/json",
        }

        response = requests.post(url, json=payload, headers=headers)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_json = response.json() if response.content else response.text
            raise ValueError(f"HTTP Error: {e}, Response: {error_json}")

        return response.json()

    def sign_single_txn(self, unsigned_txn_hex: str) -> str:
        try:
            # Decode hex transaction to bytes
            txn_bytes = bytes.fromhex(unsigned_txn_hex)

            # Double SHA256 hash of the transaction bytes
            first_hash = hashlib.sha256(txn_bytes).digest()
            txn_hash = hashlib.sha256(first_hash).digest()

            # Create signing key from private key bytes
            signing_key = SigningKey.from_string(
                self.deso_keypair.private_key, curve=SECP256k1)

            # Sign the hash
            signature = signing_key.sign_digest(
                txn_hash, sigencode=sigencode_der)

            # Convert signature to hex
            signature_hex = signature.hex()

            return signature_hex

        except Exception as e:
            return None

    def submit_txn(self, unsigned_txn_hex: str, signature_hex: str) -> dict:
        submit_url = f"{self.node_url}/api/v0/submit-transaction"

        payload = {
            "UnsignedTransactionHex": unsigned_txn_hex,
            "TransactionSignatureHex": signature_hex
        }

        headers = {
            "Origin": self.node_url,
            "Content-Type": "application/json"
        }

        response = requests.post(
            submit_url,
            data=json.dumps(payload),
            headers=headers
        )

        if response.status_code != 200:
            print(f"Error status returned from {submit_url}: {
                  response.status_code}, {response.text}")
            raise ValueError(
                f"Error status returned from {submit_url}: "
                f"{response.status_code}, {response.text}"
            )

        return response.json()

    def submit_atomic_txn(
            self,
            incomplete_atomic_txn_hex: str,
            unsigned_inner_txn_hexes: List[str],
            txn_signatures_hex: List[str]
    ) -> Dict[str, Any]:
        endpoint = "/api/v0/submit-atomic-transaction"
        url = f"{self.node_url}{endpoint}"

        payload = {
            "IncompleteAtomicTransactionHex": incomplete_atomic_txn_hex,
            "UnsignedInnerTransactionsHex": unsigned_inner_txn_hexes,
            "TransactionSignaturesHex": txn_signatures_hex
        }

        response = requests.post(url, json=payload)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                error_json = response.json()
            except ValueError:
                error_json = response.text
            raise requests.exceptions.HTTPError(
                f"Error status returned from {url}: {
                    response.status_code}, {error_json}"
            )

        return response.json()
    
    def get_transaction(self, txn_hash_hex: str, committed_txns_only: bool) -> Dict[str, Any]:
        url = f"{self.node_url}/api/v0/get-txn"

        # Determine the transaction status based on the argument
        txn_status = "Committed" if committed_txns_only else "InMempool"

        payload = {
            "TxnHashHex": txn_hash_hex,
            "TxnStatus": txn_status,
        }

        headers = {
            "Origin": self.node_url,
            "Content-Type": "application/json",
        }

        response = requests.post(url, json=payload, headers=headers)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_json = response.json()  # Get the error response JSON
            raise requests.exceptions.HTTPError(f"HTTP Error: {e}, Response: {error_json}")

        return response.json()
    
    def wait_for_commitment_with_timeout(self, txn_hash_hex: str, timeout_seconds: float) -> None:
        start_time = time.time()

        while True:
            try:
                txn_response = self.get_transaction(txn_hash_hex, committed_txns_only=True)
                if txn_response.get("TxnFound", False):
                    return  # Transaction is confirmed
            except RequestException as e:
                raise Exception(f"Error getting txn from node: {str(e)}")

            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(f"Timeout waiting for txn to confirm: {txn_hash_hex}")

            time.sleep(0.1)  # Sleep for 100 milliseconds before retrying

    def sign_and_submit_txn(self, resp: Dict[str, Any]) -> Dict[str, Any]:
        unsigned_txn_hex = resp.get('TransactionHex')
        if unsigned_txn_hex is None:
            raise ValueError("TransactionHex not found in response")
        if 'InnerTransactionHexes' in resp:
            unsigned_inner_txn_hexes = resp.get('InnerTransactionHexes')
            signature_hexes = []
            for unsigned_inner_txn_hex in unsigned_inner_txn_hexes:
                signature_hex = self.sign_single_txn(unsigned_inner_txn_hex)
                signature_hexes.append(signature_hex)
            return self.submit_atomic_txn(
                unsigned_txn_hex, unsigned_inner_txn_hexes, signature_hexes
            )
        signature_hex = self.sign_single_txn(unsigned_txn_hex)
        return self.submit_txn(unsigned_txn_hex, signature_hex)

    def coins_to_base_units(self, coin_amount: float, is_deso: bool, hex_encode: bool = False) -> str:
        if is_deso:
            base_units = int(coin_amount * 1e9)
        else:
            base_units = int(coin_amount * 1e18)
        if hex_encode:
            return hex(base_units)
        return str(base_units)


def main():
    # Configuration YOGAR configuration
    SEED_HEX = os.getenv("SEED_HEX")
    IS_TESTNET = False
    NODE_URL = "https://test.deso.org" if IS_TESTNET else "https://node.deso.org"
    explorer_link = "https://testnet.deso.org" if IS_TESTNET else "https://deso.org"

    # Initialize the client
    client = DeSoDexClient(
        is_testnet=IS_TESTNET,
        seed_phrase_or_hex=SEED_HEX,
        node_url=NODE_URL
    )

    # Your public key (replace with actual)
    string_pubkey = os.getenv("PUBLIC_KEY")

    print("\n---- Submit Post ----")
    try:    
        print('Constructing submit-post txn...')
        post_response = client.submit_post(
            updater_public_key_base58check=string_pubkey,
            body="IT WORKED!",
            parent_post_hash_hex="",  # Example parent post hash
            title="",
            image_urls=[],
            video_urls=[],
            post_extra_data={"Node": "1"},
            min_fee_rate_nanos_per_kb=1000,
            is_hidden=False,
            in_tutorial=False
        )
        print('Signing and submitting txn...')
        submitted_txn_response = client.sign_and_submit_txn(post_response)
        txn_hash = submitted_txn_response['TxnHashHex']
        print(f'Waiting for commitment... Hash = {txn_hash}. Find on {explorer_link}/txn/{txn_hash}. Sometimes it takes a minute to show up on the block explorer.')
        client.wait_for_commitment_with_timeout(txn_hash, 30.0)
        print('SUCCESS!')
    except Exception as e:
        print(f"ERROR: Submit post call failed: {e}")


if __name__ == "__main__":
    main()
