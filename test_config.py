
import os

MYSQL_HOST="localhost"
MYSQL_USER="acserver"
MYSQL_PASS="acserverzz"
MYSQL_DB="acserver"

if 'ACNODE_ACSERVER_HOST' in os.environ:
  ACNODE_ACSERVER_HOST=os.environ['ACNODE_ACSERVER_HOST']
else:
  ACNODE_ACSERVER_HOST="localhost"
ACNODE_ACSERVER_PORT=1234

# either django or php
TESTMODE="django"

if TESTMODE == "django":
  ACNODE_ACSERVER_PORT=8000
  # path to the acserver-django code, if not in ../
  ACNODE_ACSERVER_DJANGO=None
