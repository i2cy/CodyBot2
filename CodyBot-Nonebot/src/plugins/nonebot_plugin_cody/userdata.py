#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: userdata
# Created on: 2023/4/28

import json
from i2cylib.database.sqlite import SqliteDB, SqlTable, SqlDtype, Sqlimit, NewSqlTable
from pathlib import Path
from pydantic import BaseModel
from hashlib import sha256

if __name__ == "__main__":
    class CODY_CONFIG:
        cody_session_cache_path = "./"
    from utils import TimeStamp, CREATOR_ID, CREATOR_GF_ID
else:
    from .config import CODY_CONFIG
    from .utils import TimeStamp, CREATOR_ID, CREATOR_GF_ID


class ImpressionFrame(BaseModel):
    id: int
    name: str
    alternatives: list
    impression: str
    last_interact_timestamp: TimeStamp
    last_interact_session_ID: int
    last_interact_session_is_group: bool
    additional_json: dict
    title: str
    is_group: bool


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

        self.__individuals_table = self.select_table("individuals")
        self.__groups_table = self.select_table("groups")

    def __init_check(self):
        """
        check and initialize database, create table when initial start or table dose not exists
        :return:
        """

        def __add_columns_of_defaults(table: NewSqlTable):
            table.add_column('id', SqlDtype.INTEGER)
            table.add_column('name', SqlDtype.TEXT)
            table.add_column('alternatives', SqlDtype.TEXT)
            table.add_column('impression', SqlDtype.TEXT)
            table.add_column('last_interact_timestamp', SqlDtype.INTEGER)
            table.add_column('last_interact_session_ID', SqlDtype.INTEGER)
            table.add_column('last_interact_session_is_group', SqlDtype.INTEGER)
            table.add_column('title', SqlDtype.TEXT)
            table.add_column('additional_json', SqlDtype.TEXT)
            table.add_limit(0, Sqlimit.PRIMARY_KEY)
            table.add_limit(1, Sqlimit.NOT_NULL)
            table.add_limit(2, Sqlimit.NOT_NULL)
            table.add_limit(3, Sqlimit.NOT_NULL)
            table.add_limit(4, Sqlimit.NOT_NULL)
            table.add_limit(5, Sqlimit.NOT_NULL)
            table.add_limit(6, Sqlimit.NOT_NULL)
            table.add_limit(7, Sqlimit.NOT_NULL)
            table.add_limit(8, Sqlimit.NOT_NULL)

        if "individuals" not in self:
            new_table = NewSqlTable("individuals")
            __add_columns_of_defaults(new_table)

            self.create_table(new_table)

        if "groups" not in self:
            new_table = NewSqlTable("groups")
            __add_columns_of_defaults(new_table)

            self.create_table(new_table)

    def update_group(self, id: int, name: str = None,
                     alternatives: str = None,
                     impression: str = None,
                     last_interact_timestamp: int = None,
                     last_interact_session_ID: int = None,
                     last_interact_session_is_group: bool = None,
                     title: str = None,
                     additional_json: dict = None):
        """
        Update impression information of a group
        :param id: int, group ID, usually QQ ID
        :param name: str, nickname that Cody would call for this group
        :param alternatives: str, list of alternative names in json text
        :param impression: str, impression text
        :param last_interact_timestamp: int, timestamp of last interact
        :param last_interact_session_ID: int, session ID of last interact session
        :param last_interact_session_is_group: bool, whether the last interact location is
        :param title: str, title for this group, e.g. 'creator', 'friends', 'enemy'
        :param additional_json: dict, additional storage in json text, can be used for plugin storage
        :return:
        """
        # when line with given id is not in table
        if id not in self.__groups_table:
            if name is None:
                name = f"Unknown_{id}"

            if alternatives is None:
                alternatives = "[]"

            if last_interact_timestamp is None:
                last_interact_timestamp = -1

            if last_interact_session_ID is None:
                last_interact_session_ID = -1

            if last_interact_session_is_group is None:
                last_interact_session_is_group = False

            if impression is None:
                impression = ""

            if title is None:
                title = ""

            if additional_json is None:
                additional_json = {}

            self.__groups_table.append(
                [
                    id,  # QQ ID in int
                    name,  # nickname in str
                    alternatives,  # alternative names in json text
                    impression,  # impression text in str
                    last_interact_timestamp,  # timestamp when last interact, -1 stands for never
                    last_interact_session_ID,  # session ID of last interact, -1 stands for none
                    last_interact_session_is_group,  # weather if last interact session is a group chat
                    title,  # title for this group, e.g. 'admin', 'close-friends', 'notice'
                    json.dumps(additional_json)  # additional json text storage for plugins
                ]
            )

        else:
            if name is not None:  # update name
                self.__groups_table.update(name, id, 'name')

            if alternatives is not None:  # update alternative names
                alternatives = json.dumps(alternatives)
                self.__groups_table.update(alternatives, id, 'alternatives')

            if impression is not None:  # update impression text
                self.__groups_table.update(impression, id, 'impression')

            if last_interact_timestamp is not None:  # update interact timestamp
                self.__groups_table.update(last_interact_timestamp, id, 'last_interact_timestamp')

            if last_interact_session_ID is not None:  # update interact session ID
                self.__groups_table.update(last_interact_session_ID, id, 'last_interact_session_ID')

            if last_interact_session_is_group is not None:  # update is_group of interact session
                self.__groups_table.update(last_interact_session_is_group, id,
                                           'last_interact_session_is_group')

            if title is not None:  # update title
                self.__groups_table.update(title, id, 'title')

            if additional_json is not None:  # update additions
                self.__groups_table.update(json.dumps(additional_json), id, 'additional_json')

    def get_group(self, id: int) -> ImpressionFrame:
        """
        get impression information of a group
        :param id: int, QQ chat group ID
        :return: ImpressionFrame
        """
        if id in self.__groups_table:
            data = self.__groups_table.get(id)
        else:
            self.update_group(id)  # if not exists, create default
            data = self.__groups_table.get(id)

        ret = ImpressionFrame(
            id=data[0],
            name=data[1],
            alternatives=json.loads(data[2]),
            impression=data[3],
            last_interact_timestamp={"timestamp": data[4]},
            last_interact_session_ID=data[5],
            last_interact_session_is_group=data[6],
            title=data[7],
            additional_json=json.loads(data[8]),
            is_group=True
        )

        return ret

    def get_individual(self, id: int) -> ImpressionFrame:
        """
        get impression information of an individual
        :param id: int, QQ ID
        :return: ImpressionFrame
        """
        if id in self.__individuals_table:
            data = self.__individuals_table.get(id)[0]
        else:
            self.update_individual(id)  # if not exists, create default
            data = self.__individuals_table.get(id)[0]

        ret = ImpressionFrame(
            id=data[0],
            name=data[1],
            alternatives=json.loads(data[2]),
            impression=data[3],
            last_interact_timestamp={"timestamp": data[4]},
            last_interact_session_ID=data[5],
            last_interact_session_is_group=data[6],
            title=data[7],
            additional_json=json.loads(data[8]),
            is_group=False
        )

        return ret

    def list_individuals(self) -> list:
        """
        return all known user ID
        :return: list
        """
        # get a list of ID of users from database
        return [ele[0] for ele in self.__individuals_table.get(column_names='id')]

    def list_groups(self) -> list:
        """
        return all known groups
        :return: list
        """
        # get a list of ID of groups from database
        return [ele[0] for ele in self.__groups_table.get(column_names='id')]

    def update_individual(self, id: int, name: str = None,
                          alternatives: list = None,
                          impression: str = None,
                          last_interact_timestamp: int = None,
                          last_interact_session_ID: int = None,
                          last_interact_session_is_group: bool = None,
                          title: str = None,
                          additional_json: dict = None):
        """
        Update impression information of an individual
        :param id: int, user ID, usually QQ ID
        :param name: str, nickname that Cody would call
        :param alternatives: list, list of alternative names in json text
        :param impression: str, impression text
        :param last_interact_timestamp: int, timestamp of last interact
        :param last_interact_session_ID: int, session ID of last interact session
        :param last_interact_session_is_group: bool, whether the last interact location is
        :param title: str, title for this user, e.g. 'creator', 'friends', 'enemy'
        :param additional_json: dict, additional storage in json text, can be used for plugin storage
        :return:
        """

        # when line with given id is not in table
        if id not in self.__individuals_table:
            id_hash = sha256(str(id).encode()).hexdigest()

            if name is None:
                if id_hash == CREATOR_ID:
                    # creator auto-correction
                    name = "Icy"
                elif id_hash == CREATOR_GF_ID:
                    # creator's girl auto-correction
                    name = "Miuto"
                else:
                    # anonymous
                    name = f"Unknown_{id}"

            if alternatives is None:
                if id_hash == CREATOR_ID:
                    # creator auto-correction
                    alternatives = json.dumps(['艾昔', 'ccy', '吸吸歪'])
                elif id_hash == CREATOR_GF_ID:
                    # creator's girl auto-correction
                    alternatives = json.dumps(['猫条'])
                else:
                    # anonymous
                    alternatives = "[]"

            if last_interact_timestamp is None:
                last_interact_timestamp = -1

            if last_interact_session_ID is None:
                last_interact_session_ID = -1

            if last_interact_session_is_group is None:
                last_interact_session_is_group = False

            if impression is None:
                impression = ""

            if title is None:
                if id_hash == CREATOR_ID:
                    # creator auto-correction
                    title = "creator(admin)"
                elif id_hash == CREATOR_GF_ID:
                    # creator's girl auto-correction
                    name = "besties(admin)"
                else:
                    # anonymous
                    title = "stranger"

            if additional_json is None:
                additional_json = {}

            self.__individuals_table.append(
                [
                    id,  # QQ ID in int
                    name,  # nickname in str
                    alternatives,  # alternative names in json text
                    impression,  # impression text in str
                    last_interact_timestamp,  # timestamp when last interact, -1 stands for never
                    last_interact_session_ID,  # session ID of last interact, -1 stands for none
                    last_interact_session_is_group,  # weather if last interact session is a group chat
                    title,  # title for this user, e.g. 'creator', 'friends', 'enemy'
                    json.dumps(additional_json)  # additional json text storage for plugins
                ]
            )

        else:
            if name is not None:  # update name
                self.__individuals_table.update(name, id, 'name')

            if alternatives is not None:  # update alternative names
                alternatives = json.dumps(alternatives)
                self.__individuals_table.update(alternatives, id, 'alternatives')

            if impression is not None:  # update impression text
                self.__individuals_table.update(impression, id, 'impression')

            if last_interact_timestamp is not None:  # update interact timestamp
                self.__individuals_table.update(last_interact_timestamp, id, 'last_interact_timestamp')

            if last_interact_session_ID is not None:  # update interact session ID
                self.__individuals_table.update(last_interact_session_ID, id, 'last_interact_session_ID')

            if last_interact_session_is_group is not None:  # update is_group of interact session
                self.__individuals_table.update(last_interact_session_is_group, id,
                                                'last_interact_session_is_group')

            if title is not None:  # update title
                self.__individuals_table.update(title, id, 'title')

            if additional_json is not None:  # update additions
                self.__individuals_table.update(json.dumps(additional_json), id, 'additional_json')


if __name__ == '__main__':
    test_file = "test_v2.2.db"
    test_uid = 2226997440

    test_db = Impression(test_file)

    a = test_db.get_individual(test_uid)
    print(f"name: {a.name}\n"
          f"id: {a.id}\n"
          f"alternatives: {a.alternatives}\n"
          f"last_ts: {a.last_interact_timestamp}\n"
          f"last_id: {a.last_interact_session_ID}\n"
          f"last_is_group: {a.last_interact_session_is_group}\n"
          f"title: {a.title}\n",
          f"additions: {a.additional_json}")

    test_db.update_individual(test_uid, last_interact_timestamp=int(a.last_interact_timestamp + 3600),
                              last_interact_session_is_group=True)

    a = test_db.get_individual(test_uid + 1)
    print(f"name: {a.name}\n"
          f"id: {a.id}\n"
          f"alternatives: {a.alternatives}\n"
          f"last_ts: {a.last_interact_timestamp}\n"
          f"last_id: {a.last_interact_session_ID}\n"
          f"last_is_group: {a.last_interact_session_is_group}\n"
          f"title: {a.title}\n"
          f"additions: {a.additional_json}")

    print('listing all users in db: {}'.format(test_db.list_individuals()))

    test_db.close()

    # pickle test
    # import pickle
    # s = pickle.dumps(test_db)
    # print("test pickle serialization result:", s)
    # s_recover: Impression = pickle.loads(s)
    # s_recover.connect()
    # a = s_recover.get_individual(test_uid)
    # print(f"name: {a.name}\n"
    #       f"id: {a.id}\n"
    #       f"alternatives: {a.alternatives}\n"
    #       f"last_ts: {a.last_interact_timestamp}\n"
    #       f"last_id: {a.last_interact_session_ID}\n"
    #       f"last_is_group: {a.last_interact_session_is_group}\n"
    #       f"additions: {a.additional_json}")
    #
    # print("test done")
