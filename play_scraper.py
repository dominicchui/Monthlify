import datetime
from time import sleep

from monthlify.data import DataManager


def main():
    username = ''
    last_scraped = 0

    # beginning of everything
    epoch = datetime.datetime.utcfromtimestamp(0)

    dm = DataManager(username)

    # find when the last log is to correctly set last_scraped
    last_log_time = dm.get_most_recent_log_time()
    print(f'last log time: {last_log_time}')
    last_log_time_ms = int((last_log_time - epoch).total_seconds() * 1000)
    print(f'last log time ms: {last_log_time_ms}')

    while True:
        # adjust for time zone UTC-6
        now = datetime.datetime.now() - datetime.timedelta(hours=-4)
        now_unix_time = int((now - epoch).total_seconds() * 1000)
        print(f'now: {now}')

        # makes calls at maximum every 2 hours (7.2e6)
        print("check if time diff > 7200000")
        print(now_unix_time - last_log_time_ms)

        if now_unix_time - last_log_time_ms > 7.2e6:
            dm.get_recent_play_data(last_log_time_ms)
            last_log_time_ms = now_unix_time


        # checks every 15 minutes in case computer has slept
        sleep(900)


if __name__ == '__main__':
    main()
