import hashlib
import json
from urllib.parse import urlparse

from config import settings
from core.logging import logger
from db.storage import BlockchainStorage



class Blockchain(object):
    def __init__(self, dao:BlockchainStorage):
        self.nodes = set()
        self.dao = dao

    def register_node(self, address: str):
        parsed_url = urlparse(address)
        netloc = parsed_url.netloc or parsed_url.path
        if netloc:
            if netloc not in self.nodes:
                self.nodes.add(netloc)
                logger.info(f"Registered new node: {netloc}")
            else:
                logger.debug(f"Node already registered: {netloc}")
        else:
            logger.error(f"Invalid URL provided for node registration: {address}")
            raise ValueError('Invalid URL')

        def valid_chain(self, chain: list[dict]) -> bool:
            # The chain is ordered from oldest to newest (index ascending).
            # We need to validate from the second block onwards.
            if not chain:
                return False

            # Validate genesis block first
            genesis_block = chain[0]
            if not genesis_block['hash'].startswith('0' * genesis_block['header']['difficulty']):  # Fixed here
                logger.warning("Chain validation failed: Genesis block PoW is invalid.")
                return False

            for i in range(1, len(chain)):
                block = chain[i]
                last_block = chain[i - 1]

                # 1. Check that the hash of the previous block in the current block's header
                #    matches the actual hash of the previous block.
                if block['header']['previous_hash'] != last_block['hash']:
                    logger.warning(f"Chain validation failed: Previous hash mismatch at index {block['index']}.")
                    return False

                # 2. Check the Proof of Work for each block.
                # Reconstruct the header to calculate its hash
                header_string = f"{block['header']['previous_hash']}{block['merkle_root']}{block['header']['timestamp']}{block['header']['nonce']}{block['header']['difficulty']}"
                calculated_hash = hashlib.sha256(header_string.encode()).hexdigest()

                if calculated_hash != block['hash']:
                    logger.warning(f"Chain validation failed: Block hash mismatch at index {block['index']}.")
                    return False

                if not block['hash'].startswith('0' * block['header']['difficulty']):  # Fixed here
                    logger.warning(f"Chain validation failed: PoW is invalid at index {block['index']}.")
                    return False

            logger.info("Full chain validation successful.")
            return True

        def valid_chain_headers(self, headers: list[dict]) -> bool:
            """
            Validates a list of block headers.
            Headers are expected to be ordered from oldest to newest (index ascending).
            """
            if not headers:
                return False

            # Validate genesis block header first
            genesis_header = headers[0]
            # Reconstruct the header to calculate its hash
            header_string = f"{genesis_header['previous_hash']}{genesis_header['merkle_root']}{genesis_header['timestamp']}{genesis_header['nonce']}{genesis_header['difficulty']}"
            calculated_hash = hashlib.sha256(header_string.encode()).hexdigest()

            if calculated_hash != genesis_header['hash']:
                logger.warning("Header validation failed: Genesis block header hash mismatch.")
                return False
            if not genesis_header['hash'].startswith('0' * genesis_header['difficulty']):
                logger.warning("Header validation failed: Genesis block header PoW is invalid.")
                return False

            for i in range(1, len(headers)):
                header = headers[i]
                prev_header = headers[i - 1]

                # 1. Check that the previous_hash in the current header matches the hash of the previous header.
                if header['previous_hash'] != prev_header['hash']:
                    logger.warning(f"Header validation failed: Previous hash mismatch at index {header['index']}.")
                    return False

                # 2. Check the Proof of Work for each header.
                # Reconstruct the header to calculate its hash
                header_string = f"{header['previous_hash']}{header['merkle_root']}{header['timestamp']}{header['nonce']}{header['difficulty']}"
                calculated_hash = hashlib.sha256(header_string.encode()).hexdigest()

                if calculated_hash != header['hash']:
                    logger.warning(f"Header validation failed: Header hash mismatch at index {header['index']}.")
                    return False

                if not header['hash'].startswith('0' * header['difficulty']):
                    logger.warning(f"Header validation failed: PoW is invalid at index {header['index']}.")
                    return False

            logger.info("Chain headers validation successful.")
            return True

        async def resolve_conflicts(self, httpx=None) -> bool:
            from core.api_core import Block as APIBlock
            neighbours = self.nodes
            new_chain = None
            max_length = self.dao.get_chain_length()
            logger.info(f"Starting conflict resolution. Current chain length: {max_length}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                for node in neighbours:
                    if node == settings.my_address:
                        continue
                    logger.info(f"Checking chain headers on node {node}...")
                    try:
                        # Step 1: Get only headers from the neighbor
                        response = await client.get(f'http://{node}/chain/headers?page_size=1')  # Get length first
                        if response.status_code != 200:
                            logger.warning(
                                f"Node {node} responded with status {response.status_code} for headers length.")
                            continue

                        length = response.json()['length']
                        logger.info(f"Node {node} has chain length: {length}")

                        if length > max_length:
                            logger.info(f"Found potentially longer chain headers on {node}. Downloading all headers...")
                            full_headers_response = await client.get(f'http://{node}/chain/headers?page_size={length}')
                            if full_headers_response.status_code == 200:
                                headers_data = full_headers_response.json()['headers']
                                if self.valid_chain_headers(headers_data):
                                    logger.info(
                                        f"Validated longer chain headers from node {node}. New length: {length}")

                                    # Step 2: If headers are valid and longer, then download the full chain
                                    logger.info(f"Headers are valid, downloading full chain from {node}...")
                                    full_chain_response = await client.get(f'http://{node}/chain?page_size={length}')
                                    if full_chain_response.status_code == 200:
                                        chain_data = full_chain_response.json()['chain']
                                        if self.valid_chain(chain_data):  # Validate full chain
                                            logger.info(f"Validated full longer chain from node {node}.")
                                            max_length = length
                                            new_chain = chain_data
                                        else:
                                            logger.warning(
                                                f"Full chain from node {node} is invalid after header validation.")
                                    else:
                                        logger.warning(
                                            f"Failed to fetch full chain from {node}. Status: {full_chain_response.status_code}")
                                else:
                                    logger.warning(f"Chain headers from node {node} are invalid.")
                            else:
                                logger.warning(
                                    f"Failed to fetch full headers from {node}. Status: {full_headers_response.status_code}")
                    except (httpx.RequestError, json.JSONDecodeError) as e:
                        logger.error(f"Could not connect to or parse data from node {node}: {e}")
                        continue

            if new_chain:
                logger.info("Replacing the current chain with a new, longer, valid chain.")
                self.dao.replace_chain(new_chain)
                self.current_transactions = []
                # Reload the in-memory chain from the database
                self.chain = [APIBlock.from_db_model(b) for b in self.dao.get_all_blocks()]
                return True

            logger.info("Current chain is authoritative. No replacement needed.")
            return False