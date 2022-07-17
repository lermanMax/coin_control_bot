from ZODB import FileStorage, DB
import BTrees
import transaction

from db_config import DB_NAME

# create storage and db. open connection
storage = FileStorage.FileStorage(DB_NAME)
db = DB(storage)
con = db.open()
root = con.root

# ----- all "tables" ------\
root.coins = BTrees.IOBTree.BTree()

# ----- ------ ------ -----/

# closing connection
transaction.commit()
con.close()
