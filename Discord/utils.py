from datetime import datetime
import pytz


def time_to_EST(time):
    """
    Convert UTC time to EST time. (FORMAT H:MM)
    """
    utc_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    est_time = utc_time.astimezone(pytz.timezone("America/New_York"))

    return str(est_time.strftime("%I:%M").lower().lstrip("0"))
