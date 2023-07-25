#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: i2cy(i2cy@outlook.com)
# Project: CodyBot2
# Filename: utils
# Created on: 2023/4/30

import time
from datetime import datetime, timedelta
from typing import Union
from pydantic import BaseModel

CREATOR_ID = "80b3456f5f8398d38d659e2d2930e26544a61f0482180d00161cae78171d8d60"
CREATOR_GF_ID = "fa06dac2564d6b1995467e83c31e270b69de53160ce4c26ca913e28ea3a8669a"


class Usage(BaseModel):
    completion_tokens: int = -1
    prompt_tokens: int = -1
    total_tokens: int = -1

    def __str__(self):
        return str(self.total_tokens)


class GPTResponse(BaseModel):
    message: str = ""
    usage: Usage = Usage()

    def __str__(self) -> str:
        return self.message

    def __getitem__(self, item):
        return self.message.__getitem__(item)

    def __iter__(self):
        return self.message.__iter__()

    def __len__(self):
        return len(self.message)


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

    def till_now(self):
        """
        return time duration until now in datetime.timedelta
        :return: tuple
        """
        now = datetime.now()
        last = datetime.fromtimestamp(self.timestamp)

        return now - last

    def till_now_str(self) -> str:
        """
        return time duration in natual language such as '1 hour ago', 'this morning', 'yesterday noon', '3 days ago'
        :return: str
        """
        weekdays = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
        months = (None, 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                  'September', 'October', 'November', 'December')

        # calculate duration
        ts_now = time.time()
        duration = ts_now - self.timestamp

        now = datetime.fromtimestamp(ts_now)
        last = datetime.fromtimestamp(self.timestamp)

        time_till_now = now - last

        delta_days = now.toordinal() - last.toordinal()
        delta_years = now.year - last.year

        if duration < 60:
            # just now
            duration_text = "just now"

        elif duration < 3600:
            # if less than 1 hour
            duration_text = "{} minute(s) ago".format(time_till_now.seconds // 60)

        elif duration < 14400:
            # if less than 4 hours
            duration_text = "{:.1f} hours ago".format(time_till_now.seconds / 3600)

        elif delta_days < 2:
            # if less than 2 days
            if delta_days == 0:
                # today
                duration_text = "today "
            else:
                # yesterday
                duration_text = "yesterday "

            if last.hour < 6:
                duration_text += "the small hours"
            elif last.hour < 11:
                duration_text += "morning"
            elif last.hour < 13:
                duration_text += "noon"
            elif last.hour < 17:
                duration_text += "afternoon"
            elif last.hour < 21:
                duration_text += "evening"
            else:
                duration_text += "night"

        elif delta_days < (now.weekday() + 1):
            # this week
            duration_text = "{} days ago on {}".format(delta_days, weekdays[last.weekday()])

        elif delta_days < now.day:
            # this month
            duration_text = "{} days ago".format(delta_days)

        elif (delta_years == 0 and now.month - last.month < 2) \
                or (delta_years == 1 and now.month - last.month == -11):
            # last month
            duration_text = "last month"

        elif delta_years == 0:
            # this year
            duration_text = "{} months ago in {}".format(now.month - last.month, months[last.month])

        elif delta_years == 1:
            # last year
            duration_text = "last {}".format(months[last.month])

        else:
            # years ago
            duration_text = "{} years ago".format(delta_years)

        return duration_text


if __name__ == '__main__':
    ts = TimeStamp(time.time())
    print("current date time:", ts)
    for i in range(40):
        if i < 18:
            ts -= 1200 * i
        elif i < 30:
            ts -= 3600 * i * 0.9 * i
        else:
            ts -= 3600 * i * 2 * i
        print("offset time:", ts)
        print("till now:", ts.till_now_str())
