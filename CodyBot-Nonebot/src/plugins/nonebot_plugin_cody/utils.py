#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: utils
# Created on: 2023/4/30

import time
from typing import Union
from pydantic import BaseModel


class TimeStamp(BaseModel):
    timestamp: Union[float, int]

    def __init__(self, timestamp: Union[int, float]):
        """
        create a timestamp object
        :param timestamp: int or float, timestamp
        """
        super().__init__(timestamp=timestamp)

    def __int__(self):
        return int(self.timestamp)

    def __float__(self):
        return float(self.timestamp)

    def __add__(self, other):
        return TimeStamp(self.timestamp + other)

    def __sub__(self, other):
        return TimeStamp(self.timestamp - other)

    def __iadd__(self, other):
        self.timestamp += other
        return self

    def __isub__(self, other):
        self.timestamp -= other
        return self

    def __lt__(self, other):
        return self.timestamp < other

    def __le__(self, other):
        return self.timestamp <= other

    def __ne__(self, other):
        return self.timestamp != other

    def __eq__(self, other):
        return self.timestamp == other

    def __gt__(self, other):
        return self.timestamp > other

    def __ge__(self, other):
        return self.timestamp >= other

    def __str__(self):
        return self.to_datetime()

    def to_datetime(self, strf: str = "%Y-%m-%d %H:%M") -> str:
        """
        convert timestamp to str
        :param strf: str (optional, default: "%Y-%m-%d %H:%M"), time format string
        :return: str
        """
        t_array = time.localtime(self.timestamp)
        ret = time.strftime(strf, t_array)
        return ret


if __name__ == '__main__':
    ts = TimeStamp(time.time())
    print("current date time:", ts)
    ts -= 8 * 3600
    print("current UTC time:", ts)
