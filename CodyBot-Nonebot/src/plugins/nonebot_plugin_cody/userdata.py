#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: userdata
# Created on: 2023/4/28

from i2cylib.database.sqlite import SqliteDB, SqlTable, SqlDtype, Sqlimit, NewSqlTable
from .config import CODY_CONFIG
from pathlib import Path

class Impression(SqliteDB):

    def __init__(self, database_filename: str = "impression.db"):
        """
        impressions of user, connected with local sqlite database
        :param database_filename: str, the filename of database, not path
        """
        super().__init__(
            Path(CODY_CONFIG.cody_session_cache_path).joinpath(database_filename).as_posix()
        )
        self.autocommit = True  # enable auto-commit
        self.connect()
        self.__init_check()

    def __init_check(self):
        """
        check and initialize database, create table when initial start or table dose not exists
        :return:
        """
        all_tables = self.list_all_tables()
        if not "private_individuals" in all_tables:
            new_table = NewSqlTable("individuals")
            new_table.add_column('id', SqlDtype.INTEGER)
            new_table.add_column('name', SqlDtype.TEXT)
            new_table.add_column('impression', SqlDtype.TEXT)
            new_table.add_column('last_met_timestamp', SqlDtype.INTEGER)
            new_table.add_column('last_met_session_ID',  SqlDtype.INTEGER)
            new_table.add_column('last_met_session_is_group', SqlDtype.INTEGER)
            new_table.add_limit(0, Sqlimit.PRIMARY_KEY)
            new_table.add_limit(0, Sqlimit.UNIQUE)
            new_table.add_limit(1, Sqlimit.NOT_NULL)
            new_table.add_limit(2, Sqlimit.NOT_NULL)
            new_table.add_limit(3, Sqlimit.NOT_NULL)
            new_table.add_limit(4, Sqlimit.NOT_NULL)
            new_table.add_limit(5, Sqlimit.NOT_NULL)

            self.create_table(new_table)

        if not "group_impression" in all_tables:
            new_table = NewSqlTable("groups")

            new_table.add_column('id', SqlDtype.INTEGER)
            new_table.add_column('name', SqlDtype.TEXT)
            new_table.add_column('impression', SqlDtype.TEXT)
            new_table.add_column('last_met_timestamp', SqlDtype.INTEGER)
            new_table.add_column('last_met_session_ID', SqlDtype.INTEGER)
            new_table.add_column('last_met_session_is_group', SqlDtype.INTEGER)
            new_table.add_limit(0, Sqlimit.PRIMARY_KEY)
            new_table.add_limit(0, Sqlimit.UNIQUE)
            new_table.add_limit(1, Sqlimit.NOT_NULL)
            new_table.add_limit(2, Sqlimit.NOT_NULL)
            new_table.add_limit(3, Sqlimit.NOT_NULL)
            new_table.add_limit(4, Sqlimit.NOT_NULL)
            new_table.add_limit(5, Sqlimit.NOT_NULL)

            self.create_table(new_table)

    def update_individual(self, id: int, name: str = None, impression: str = None,
                          last_met_timestamp: int = None,
                          last_met_session_ID: int = None,
                          last_met_session_is_group: bool = None):
        """
        update impression information of an individual
        :param id: int, user ID, usually QQ ID
        :param name: str, nickname that Cody would call him
        :param impression: str, impression text
        :param last_met_timestamp: int, timestamp of last interact
        :param last_met_session_ID: int, session ID of last interact session
        :param last_met_session_is_group: bool, whether the last interact location is
        :return:
        """
        # TODO: finish this method

