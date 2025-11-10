"""Utilities for mucking about with lava DAG components."""

from __future__ import annotations

import csv
import re
import sqlite3

import openpyxl

try:
    from lava.connection import get_pysql_connection
except ImportError:  # pragma: no cover
    get_pysql_connection = None  # pragma: no cover

DEFAULT_TABLE = 'dag'

__author__ = 'Murray Andrews'


# ---------------------------------------------------------------------------------------
def load_dag_from_csv(filename: str) -> dict[str, set[str]]:
    """
    Load dependency graph from a CSV file.

    Predecessor jobs are across the top. Dependent jobs are the first column.

    :param filename:    Source file name.
    :return:            Dependency map.
    """

    dag = {}
    with open(filename, encoding='utf-8') as fp:
        reader = csv.reader(fp)

        predecessors = [job.strip() for job in next(reader)]
        for row in reader:
            job = row[0].strip()
            if not job:
                continue
            dag.setdefault(row[0], set())
            dag[job] |= {
                depends_on
                for depends_on, flag in zip(predecessors[1:], row[1:])
                if flag.strip() and depends_on != job
            }

    return dag


# ---------------------------------------------------------------------------------------
def load_dag_from_xlsx(filename: str, worksheet=None) -> dict[str, set[str]]:
    """
    Load dependency graph from an Excel (xslx) file.

    Predecessor jobs are across the top. Dependent jobs are the first column.

    :param filename:    Source file name.
    :param worksheet:   Use the specified worksheet. If not specified use the first one.
    :return:            Dependency map.
    """

    dag = {}
    wb = None

    try:
        wb = openpyxl.load_workbook(filename=filename)
        ws = wb[worksheet if worksheet else wb.sheetnames[0]]
        matrix = ws.values
        predecessors = [job.strip() for job in next(matrix)]
        for row in matrix:
            job = row[0].strip() if row[0] else row[0]
            if not job:
                continue
            dag.setdefault(row[0], set())
            dag[job] |= {
                depends_on
                for depends_on, flag in zip(predecessors[1:], row[1:])
                if flag and flag.strip() and depends_on != job
            }
    finally:
        if wb:
            wb.close()

    return dag


# ---------------------------------------------------------------------------------------
def load_dag_from_db(db_conn, table: str = DEFAULT_TABLE, group: str = None) -> dict[str, set[str]]:
    """
    Load dependency matrix from a database table.

    The table must have a schema something like this:

    ```sql
    CREATE TABLE dag (
        job_group VARCHAR(50),
        job VARCHAR(50) NOT NULL,
        depends_on VARCHAR(50)
    );
    ```

    :param db_conn:     A DBAPI 2.0 connection.
    :param table:       Source table name.
    :param group:       Filter value to select a group of dependency entries.
    :return:            Dependency map.
    """

    if not re.match(r'^(\w+\.)?\w+$', table):
        raise ValueError(f'Bad table name: {table}')

    # We don't know the paramstyle.
    sql = f'SELECT job, depends_on FROM {table}'  # noqa: S608
    if group:
        if not re.match(r'^\w+$', group):
            raise ValueError(f'Only alphanumerics allowed: {group}')
        sql += f" WHERE job_group='{group}'"

    cursor = db_conn.cursor()

    cursor.execute(sql)
    dag = {}
    for row in cursor.fetchall():
        job = row[0].strip() if row[0] else row[0]
        if not job:
            continue
        dag.setdefault(job, set())
        depends_on = row[1].strip() if row[1] else row[1]
        if job != depends_on:
            dag[job].add(depends_on)

    return dag


# ---------------------------------------------------------------------------------------
def load_dag_from_sqlite3(
    filename: str, table: str = DEFAULT_TABLE, group: str = None
) -> dict[str, set[str]]:
    """
    Load dependency matrix from an SQLite3 database.

    :param filename:    Source file name.
    :param table:       Source table in the database.
    :param group:       Filter value to select a group of dependency entries.
    :return:            Dependency map.
    """

    with sqlite3.connect(filename) as conn:
        return load_dag_from_db(conn, table=table, group=group)


# ---------------------------------------------------------------------------------------
def load_dag_from_lava_conn(
    conn_id: str, realm: str, table: str = DEFAULT_TABLE, group: str = None
) -> dict[str, set[str]]:
    """
    Load dependency matrix from an RDBMS via a lava connector.

    :param conn_id:     Lava connection ID.
    :param realm:       Lava realm.
    :param table:       Source table in the database.
    :param group:       Filter value to select a group of dependency entries.
    :return:            Matrix of data.
    """

    if not get_pysql_connection:
        raise Exception(
            'lava support not enabled -- install the lava package to enable'
        )  # pragma: no cover

    conn = get_pysql_connection(conn_id, realm)
    try:
        return load_dag_from_db(conn, table=table, group=group)
    finally:
        conn.close()
