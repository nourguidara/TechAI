import argparse
from pathlib import Path
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--confirm',action='store_true'); args=p.parse_args()
    root=(Path.cwd()/'data'/'mail').resolve()
    if not args.confirm: p.error('Explicit --confirm required')
    if root.parent!=(Path.cwd()/'data').resolve(): raise ValueError('Unsafe mail path')
    for item in root.glob('*.eml'):
        if item.resolve().parent!=root or item.is_symlink(): raise ValueError('Unsafe mail file')
        item.unlink()
    print('Deleted local sandbox captured email only. Mailpit messages are reset separately in its UI.')
