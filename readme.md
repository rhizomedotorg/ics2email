## ics2email

ics2email processes an ics url and sends new or modified events to the specified recipients. Event history is global and not user specific, so a newly added user will only get future notifications.

Install requirements
```shell
pip install -r requirements.txt
```

To run, first copy the `config.example.yaml` to `config.yaml` and fill out the appropriate fields. Then run:
```shell
python ics2email.py
```

The script stores previously seen events in a sqlite database called `calendar-data.db` so ensure the script has write access and persistent storage.