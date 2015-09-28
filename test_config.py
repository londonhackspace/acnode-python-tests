MYSQL_HOST="localhost"
MYSQL_USER="acserver"
MYSQL_PASS="acserverzz"
MYSQL_DB="acserver"

ACNODE_ACSERVER_HOST="localhost"
ACNODE_ACSERVER_PORT=1234

# either django or php
TESTMODE="django"

if TESTMODE == "django":
  ACNODE_ACSERVER_PORT=8000
  # path to the acserver-django code, if not in ../
  ACNODE_ACSERVER_DJANGO=None
