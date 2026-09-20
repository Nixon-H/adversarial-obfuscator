"""Encryption module — Stage 4 post-link per-block encryption.

Provides the CLI (`python -m encrypt`) and re-exports the public API for
ELF binary encryption (bulk or per-block), NIX container packing/unpacking,
and AES-256 seed generation.

Public API:
    - encrypt_binary(input, output, seed, block_size, ...) -> dict
    - encrypt_binary_per_block(input, output, seed, block_size, ...) -> dict
    - pack_encrypted_payload(path, key) -> bytes
    - unpack_encrypted_payload(container, key) -> bytes
    - container_info(container) -> dict
    - generate_encryption_seed() -> bytes

Dependencies:
    - encrypt.encrypt, encrypt.container, encrypt.aes
"""

import argparse
import sys

from . import encrypt as _encrypt
from . import container as _container
from . import aes as _aes

__all__ = ['encrypt_binary', 'encrypt_binary_per_block',
           'pack_encrypted_payload', 'unpack_encrypted_payload',
           'container_info', 'generate_encryption_seed']


def encrypt_binary(*args, **kwargs):
    return _encrypt.encrypt_binary(*args, **kwargs)


def encrypt_binary_per_block(*args, **kwargs):
    return _encrypt.encrypt_binary_per_block(*args, **kwargs)


def pack_encrypted_payload(*args, **kwargs):
    return _container.pack_encrypted_payload(*args, **kwargs)


def unpack_encrypted_payload(*args, **kwargs):
    return _container.unpack_encrypted_payload(*args, **kwargs)


def container_info(*args, **kwargs):
    return _container.container_info(*args, **kwargs)


def generate_encryption_seed():
    return _aes.generate_encryption_seed()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog='python -m encrypt',
        description='Nixon Stage 4: Post-Link Per-Block Encryption',
    )
    sub = parser.add_subparsers(dest='command', help='Sub-command')

    enc_parser = sub.add_parser('encrypt', help='Encrypt an ELF binary')
    enc_parser.add_argument('input', help='Input ELF binary path')
    enc_parser.add_argument('-o', '--output', required=True,
                            help='Output encrypted binary path')
    enc_parser.add_argument('--seed', type=lambda x: bytes.fromhex(x),
                            help='32-byte hex seed for key derivation')
    enc_parser.add_argument('--block-size', type=int, default=64,
                            help='Encryption block size (default: 64)')
    enc_parser.add_argument('--per-block', action='store_true',
                            help='Use per-block stubs (may break cross-block jumps)')

    pack_parser = sub.add_parser('pack', help='Pack a file into NIX container')
    pack_parser.add_argument('input', help='Input file to encrypt')
    pack_parser.add_argument('-o', '--output', required=True,
                             help='Output container path')
    pack_parser.add_argument('--key', type=lambda x: bytes.fromhex(x),
                             required=True,
                             help='32-byte hex encryption key')

    unpack_parser = sub.add_parser('unpack', help='Unpack a NIX container')
    unpack_parser.add_argument('input', help='Input container path')
    unpack_parser.add_argument('-o', '--output', required=True,
                               help='Output decrypted file path')
    unpack_parser.add_argument('--key', type=lambda x: bytes.fromhex(x),
                               required=True,
                               help='32-byte hex decryption key')

    info_parser = sub.add_parser('info', help='Show container info')
    info_parser.add_argument('input', help='Input container path')

    gen_parser = sub.add_parser('gen-seed', help='Generate a random 32-byte seed')

    args = parser.parse_args(argv)

    if args.command == 'encrypt':
        if args.per_block:
            result = _encrypt.encrypt_binary_per_block(
                args.input, args.output,
                seed=args.seed, block_size=args.block_size,
            )
        else:
            result = _encrypt.encrypt_binary(
                args.input, args.output,
                seed=args.seed, block_size=args.block_size,
            )
        print(f'Encrypted {result["num_blocks"]} blocks ({result["block_size"]}B each)')
        print(f'  Seed:          {result["seed"]}')
        print(f'  Entry point:   {result["entry_point"]}')
        print(f'  Original text: {result["text_size"]} bytes')
        print(f'  Stub size:     {result["stub_size"]} bytes')

    elif args.command == 'pack':
        container = _container.pack_encrypted_payload(args.input, args.key)
        with open(args.output, 'wb') as f:
            f.write(container)
        info = _container.container_info(container)
        print(f'Packed: {info["original_size"]} -> {info["total_size"]} bytes')

    elif args.command == 'unpack':
        with open(args.input, 'rb') as f:
            container = f.read()
        plaintext = _container.unpack_encrypted_payload(container, args.key)
        with open(args.output, 'wb') as f:
            f.write(plaintext)
        print(f'Unpacked: {len(plaintext)} bytes -> {args.output}')

    elif args.command == 'info':
        with open(args.input, 'rb') as f:
            container = f.read()
        info = _container.container_info(container)
        for k, v in info.items():
            print(f'  {k}: {v}')

    elif args.command == 'gen-seed':
        seed = _aes.generate_encryption_seed()
        print(seed.hex())

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
