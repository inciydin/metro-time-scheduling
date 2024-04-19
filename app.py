import os
from datetime import datetime
from math import ceil

import pandas as pd

input_file = (
    input("Yolcu verisini içeren CSV dosyasının adını giriniz (Varsayılan: hourly_transportation_202401.csv): ")
    or "hourly_transportation_202401.csv"
)

try:
    data = pd.read_csv(input_file)
except Exception as e:
    print(f"Please provide a valid input file. Error: {e}")
    exit(1)


vehicle_capacity = int(input("Aracın yolcu kapasitesini giriniz (Varsayılan: 2600): ") or 2600)
possible_values = [
    int(x)
    for x in input("Olabilecek sefer aralık sürelerini (dk) giriniz (Varsayılan: 4, 5, 6, 7, 8, 10, 12, 15): ")
    or "4, 5, 6, 7, 8, 10, 12, 15".split(", ")
]

filtered = data[(data["road_type"] == "RAYLI") & (data["line"] == "YENIKAPI - HACIOSMAN")]

total_counts = {}

for row in filtered.itertuples():
    date = row.transition_date
    hour = str(row.transition_hour)
    if date not in total_counts:
        total_counts[date] = {}
    if hour not in total_counts[date]:
        total_counts[date][hour] = 0
    total_counts[date][hour] += 1


def divide_items_into_groups(total_items):
    group_count = 3
    base_group_size = total_items // group_count
    remainder = total_items % group_count
    groups = [base_group_size] * group_count

    for i in range(remainder):
        groups[i] += 1

    return {"0": groups[0], "20": groups[1], "40": groups[2]}


group_counts = {}

for date, date_value in total_counts.items():
    group_counts[date] = {}
    for hour, count in date_value.items():
        group_counts[date][hour] = divide_items_into_groups(count)

sums = {}

for row in filtered.itertuples():
    date = row.transition_date
    hour = str(row.transition_hour)

    if date not in sums:
        sums[date] = {}
    if hour not in sums[date]:
        sums[date][hour] = {
            "0": {"count": 0, "value": 0},
            "20": {"count": 0, "value": 0},
            "40": {"count": 0, "value": 0},
        }

    i = None

    if sums[date][hour]["0"]["count"] < group_counts[date][hour]["0"]:
        i = "0"
    elif sums[date][hour]["20"]["count"] < group_counts[date][hour]["20"]:
        i = "20"
    elif sums[date][hour]["40"]["count"] < group_counts[date][hour]["40"]:
        i = "40"

    if i is not None:
        sums[date][hour][i]["count"] += 1
        sums[date][hour][i]["value"] += row.number_of_passage


def get_day(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    day = date_obj.strftime("%A")
    if day in ["Saturday", "Sunday"]:
        return day.lower()
    return "weekday"


sums_by_days = {
    "weekday": {},
    "saturday": {},
    "sunday": {},
}

for date, date_value in sums.items():
    day_of_week = get_day(date)

    for hour, hour_value in date_value.items():
        if hour not in sums_by_days[day_of_week]:
            sums_by_days[day_of_week][hour] = {
                "0": {"value": 0, "count": 0},
                "20": {"value": 0, "count": 0},
                "40": {"value": 0, "count": 0},
            }

        for i in ["0", "20", "40"]:
            sums_by_days[day_of_week][hour][i]["value"] += hour_value[i]["value"]
            sums_by_days[day_of_week][hour][i]["count"] += 1

means_by_intervals = {
    "weekday": {},
    "saturday": {},
    "sunday": {},
}

for day, day_value in sums_by_days.items():
    for hour, hour_value in day_value.items():
        if hour not in means_by_intervals[day]:
            means_by_intervals[day][hour] = {}

        for minute, minute_value in hour_value.items():
            means_by_intervals[day][hour][minute] = minute_value["value"] / minute_value["count"]

means_df = pd.DataFrame(
    columns=[
        "weekday_0",
        "weekday_20",
        "weekday_40",
        "saturday_0",
        "saturday_20",
        "saturday_40",
        "sunday_0",
        "sunday_20",
        "sunday_40",
    ]
)

for day, day_value in means_by_intervals.items():
    for hour, hour_value in day_value.items():
        for minute, mean in hour_value.items():
            col_name = f"{day}_{minute}"
            if hour not in means_df.index:
                means_df.loc[hour] = pd.Series(dtype="float")
            means_df.at[hour, col_name] = mean

means_df_filtered = means_df.drop(index=["0", "1", "2", "3", "4", "5"]).astype("int")
means_df_filtered.to_csv("mean.csv")
print("Ortalama yolcu sayıları mean.csv dosyasına yazıldı.")


def find_nearest(value, round_list):
    greater_values = [num for num in round_list if num > value]

    if greater_values:
        return min(greater_values, key=lambda x: abs(x - value))
    else:
        return min(round_list, key=lambda x: abs(x - value))


def calc_mins_between_vhcs(vehicle_capacity, time_interval, passenger_demand, possible_values=None):
    value = time_interval * vehicle_capacity / passenger_demand

    if possible_values:
        return value, find_nearest(value, possible_values)
    return value, ceil(value)


time_interval = 20

exact_value, result = calc_mins_between_vhcs(vehicle_capacity, time_interval, 5000, possible_values=possible_values)

apply_fn = lambda x: calc_mins_between_vhcs(vehicle_capacity, time_interval, x, possible_values=possible_values)[1]

calculated = means_df_filtered.apply(lambda x: x.map(apply_fn))
calculated.to_csv("calculated.csv")
print("Hesaplanan süreler calculated.csv dosyasına yazıldı.")
