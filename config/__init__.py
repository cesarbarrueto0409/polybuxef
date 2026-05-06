import pymysql

pymysql.install_as_MySQLdb()

# Django 6 validates the mysqlclient version even when PyMySQL provides the
# MySQLdb compatibility layer. PyMySQL is used here to avoid native MySQL
# client dependencies in local development.
pymysql.version_info = (2, 2, 1, 'final', 0)
