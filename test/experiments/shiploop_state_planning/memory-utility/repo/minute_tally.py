ACTIVITIES = [
    {"label": "warmup", "minutes": 10},
    {"label": "practice", "minutes": 25},
    {"label": "review", "minutes": 5},
]


def activity_labels(activities):
    return [activity["label"] for activity in activities]


def main():
    for label in activity_labels(ACTIVITIES):
        print(label)


if __name__ == "__main__":
    main()

