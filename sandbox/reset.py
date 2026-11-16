import argparse
from pathlib import Path
from sqlalchemy import delete
from backend.config import settings
from backend.database import Base,engine,init_db

def reset(confirm=False,orders_only=False):
    path=Path(settings.database_url.removeprefix('sqlite:///')).resolve()
    root=(Path.cwd()/'data').resolve()
    if not confirm or path.parent!=root or path.name not in ('techstock.db','evaluation.db','test.db'):
        raise ValueError('Reset requires --confirm and a recognized project data database')
    from backend import models
    if orders_only:
        with engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                if table.name not in ('products','supplier_offers'): connection.execute(delete(table))
    else:
        Base.metadata.drop_all(engine); init_db()
    checkpoint=path.with_suffix('.checkpoints.db')
    for candidate in (checkpoint,Path(str(checkpoint)+'-wal'),Path(str(checkpoint)+'-shm')):
        if candidate.resolve().parent!=root or candidate.is_symlink(): raise ValueError('Unsafe checkpoint path')
        if candidate.exists(): candidate.unlink()
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--confirm',action='store_true'); p.add_argument('--orders-only',action='store_true'); a=p.parse_args()
    reset(a.confirm,a.orders_only); print('Reset sandbox tables and corresponding checkpoints. Catalog preserved only with --orders-only.')
