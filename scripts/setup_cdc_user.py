import pymysql

def main():
    conn = pymysql.connect(host='localhost', port=3306, user='root', password='')
    cur = conn.cursor()
    with open('scripts/init-cdc-user.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if stmt:
            print("Executing:", stmt)
            cur.execute(stmt)
    conn.commit()
    cur.execute("SELECT user, host FROM mysql.user WHERE user = 'debezium_user'")
    print("User rows:", cur.fetchall())
    cur.execute("SHOW GRANTS FOR 'debezium_user'@'%'")
    for g in cur.fetchall():
        print("Grant:", g[0])
    conn.close()

if __name__ == '__main__':
    main()
