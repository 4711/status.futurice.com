from time import time
import json
import MySQLdb
import logging
import datetime

from rt_settings import *

class RTStats:
    def __init__(self):
        self.username = RT_USERNAME
        self.password = RT_PASSWORD
        self.database = RT_DATABASE
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = self.connect()
        return self._db

    def connect(self):
        return MySQLdb.connect(passwd=self.password, db=self.database, user=self.username)

    def disconnect(self):
        pass

    def send_data(self, name, data):
        data_dump = json.dumps({"name": name, "data": data}, sort_keys=True, indent=4)
        open(name+".data.json", "w").write(data_dump)

    def run(self):
        self.get_ticket_stats()

    def get_ticket_stats(self):
        def get_one(query):
            c = self.db.cursor()
            c.execute(query)
            (count,) = c.fetchone()
            return count

        def get_two(query):
            c = self.db.cursor()
            c.execute(query)
            (name, count) = c.fetchone()
            return {"name": name, "count": count}

        def get_two_all(query):
            c = self.db.cursor()
            c.execute(query)
            items = c.fetchall()
            ret = {}
            for name, count in items:
                ret[name] = count
            
            return ret
            

        data = {}
        # total number of tickets, including automatic
        data["all_tickets"] = get_one("select count(*) as c from Tickets;")
        # total number of tickets with unique subject
        data["all_tickets_unique"] = get_one("select count(DISTINCT Subject) as c from Tickets;")

        dates = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        xtitles = [a for a in range(0, 24)]

        dates_stats = {}
        data["dots"] = {}

        for item, query in [("all", "select DATE_FORMAT(Created, '%%H') as timestamp, count(*) as c from Tickets where DATE_FORMAT(Created, '%%a')='%s' group by timestamp;"), 
                          ("manual", "select DATE_FORMAT(Created, '%%H') as timestamp, count(*) as c from Tickets where Queue=1 and DATE_FORMAT(Created, '%%a')='%s' group by timestamp;"), 
                    ("all_resolved", "select DATE_FORMAT(Resolved, '%%H') as timestamp, count(*) as c from Tickets where DATE_FORMAT(Resolved, '%%a')='%s' group by timestamp;"),
                 ("manual_resolved", "select DATE_FORMAT(Resolved, '%%H') as timestamp, count(*) as c from Tickets where Queue=1 and DATE_FORMAT(Resolved, '%%a')='%s' group by timestamp;")]:
            data["dots"][item] = {}
            data["dots"][item]["ytitles"] = dates
            data["dots"][item]["xtitles"] = []

            for hour in xtitles:
                tmp3 = str(hour).strip()
                if len(tmp3) == 1:
                    tmp3 = "0"+tmp3
                data["dots"][item]["xtitles"].append(tmp3)
            data["dots"][item]["date_stats"] = []

            for day in dates:
                tmp = get_two_all(query % day)
                for xtitle in xtitles:
                    tmp3 = str(xtitle).strip()
                    if len(tmp3) == 1:
                        tmp3 = "0"+tmp3
                    data["dots"][item]["date_stats"].append(tmp.get(tmp3, None))
            data["dots"][item]["date_stats"] = data["dots"][item]["date_stats"][-3:] + data["dots"][item]["date_stats"][:-3]

        # number of unique subjects
        data["unique_manual"] = get_one("select count(distinct(Subject)) as c from Tickets where Queue=1;")
        # new tickets during last 7 days
        data["unique_manual_7d"] = get_one("select count(DISTINCT Subject) as c from Tickets where Created >= date_sub(current_date, INTERVAL 7 day) and Queue=1;")
        # new tickets during last 30 days
        data["unique_manual_30d"] = get_one("select count(DISTINCT Subject) as c from Tickets where Created >= date_sub(current_date, INTERVAL 30 day) and Queue=1;")
        # new tickets during last 365 days
        data["unique_manual_365d"] = get_one("select count(DISTINCT Subject) as c from Tickets where Created >= date_sub(current_date, INTERVAL 365 day) and Queue=1;")

        # general tickets per day
        data["created_per_day"] = get_two_all("select DATE_FORMAT(Created, '%a') as timestamp, count(*) as c from Tickets where Queue=1 group by timestamp;")
        data["created_per_day_7d"] = get_two_all("select DATE_FORMAT(Created, '%a') as timestamp, count(*) as c from Tickets where Queue=1 and Created >= date_sub(current_date, INTERVAL 7 day) group by timestamp;")
        data["created_per_day_30d"] = get_two_all("select DATE_FORMAT(Created, '%a') as timestamp, count(*) as c from Tickets where Queue=1 and Created >= date_sub(current_date, INTERVAL 30 day) group by timestamp;")
        data["created_per_day_365d"] = get_two_all("select DATE_FORMAT(Created, '%a') as timestamp, count(*) as c from Tickets where Queue=1 and Created >= date_sub(current_date, INTERVAL 365 day) group by timestamp;")

        # general tickets per hour
        data["created_per_hour"] = get_two_all("select DATE_FORMAT(Created, '%H') as timestamp, count(*) as c from Tickets where Queue=1 group by timestamp;")
        data["created_per_hour_7d"] = get_two_all("select DATE_FORMAT(Created, '%H') as timestamp, count(*) as c from Tickets where Queue=1 and Created >= date_sub(current_date, INTERVAL 7 day) group by timestamp;")
        data["created_per_hour_30d"] = get_two_all("select DATE_FORMAT(Created, '%H') as timestamp, count(*) as c from Tickets where Queue=1 and Created >= date_sub(current_date, INTERVAL 30 day) group by timestamp;")
        data["created_per_hour_365d"] = get_two_all("select DATE_FORMAT(Created, '%H') as timestamp, count(*) as c from Tickets where Queue=1 and Created >= date_sub(current_date, INTERVAL 365 day) group by timestamp;")

        # general tickets per day
        data["resolved_per_day"] = get_two_all("select DATE_FORMAT(Resolved, '%a') as timestamp, count(*) as c from Tickets where Queue=1 group by timestamp;")
        data["resolved_per_day_7d"] = get_two_all("select DATE_FORMAT(Resolved, '%a') as timestamp, count(*) as c from Tickets where Queue=1 and Resolved >= date_sub(current_date, INTERVAL 7 day) group by timestamp;")
        data["resolved_per_day_30d"] = get_two_all("select DATE_FORMAT(Resolved, '%a') as timestamp, count(*) as c from Tickets where Queue=1 and Resolved >= date_sub(current_date, INTERVAL 30 day) group by timestamp;")
        data["resolved_per_day_365d"] = get_two_all("select DATE_FORMAT(Resolved, '%a') as timestamp, count(*) as c from Tickets where Queue=1 and Resolved >= date_sub(current_date, INTERVAL 365 day) group by timestamp;")

        # general tickets per hour
        data["resolved_per_hour"] = get_two_all("select DATE_FORMAT(Resolved, '%H') as timestamp, count(*) as c from Tickets where Queue=1 group by timestamp;")
        data["resolved_per_hour_7d"] = get_two_all("select DATE_FORMAT(Resolved, '%H') as timestamp, count(*) as c from Tickets where Queue=1 and Resolved >= date_sub(current_date, INTERVAL 7 day) group by timestamp;")
        data["resolved_per_hour_30d"] = get_two_all("select DATE_FORMAT(Resolved, '%H') as timestamp, count(*) as c from Tickets where Queue=1 and Resolved >= date_sub(current_date, INTERVAL 30 day) group by timestamp;")
        data["resolved_per_hour_365d"] = get_two_all("select DATE_FORMAT(Resolved, '%H') as timestamp, count(*) as c from Tickets where Queue=1 and Resolved >= date_sub(current_date, INTERVAL 365 day) group by timestamp;")

        # general tickets per day
        dictlist = [("created_futu", 
		get_two_all("select DATE_FORMAT(Tickets.Created, '%j') as timestamp, count(*) as c from Tickets, Users where Tickets.Created >= date_sub(current_date, INTERVAL 120 day) and Tickets.Creator=Users.id and Users.EmailAddress like '%.%@futurice.com' and Users.EmailAddress not in ('phaser@futurice.com', 'mailman@futurice.com', 'noreply@futurice.com', 'zabbix@futurice.com') group by timestamp;")
         ), ("created_other",
 		get_two_all("select DATE_FORMAT(Tickets.Created, '%j') as timestamp, count(*) as c from Tickets, Users where Tickets.Created >= date_sub(current_date, INTERVAL 120 day) and Tickets.Creator=Users.id and Users.EmailAddress not like '%@%futurice.com' group by timestamp;")
         ), ("created_machine",
 		get_two_all("select DATE_FORMAT(Tickets.Created, '%j') as timestamp, count(*) as c from Tickets, Users where Tickets.Created >= date_sub(current_date, INTERVAL 120 day) and Tickets.Creator=Users.id and (Users.EmailAddress like '%@%.futurice.com' or Users.EmailAddress in ('zabbix@futurice.com', 'mailman@futurice.com', 'noreply@futurice.com')) group by timestamp;")
         ), ("resolved_futu",
 		get_two_all("select DATE_FORMAT(Tickets.Resolved, '%j') as timestamp, count(*) as c from Tickets, Users where Tickets.Resolved >= date_sub(current_date, INTERVAL 120 day) and Tickets.Creator=Users.id and Users.EmailAddress like '%.%@futurice.com' and Users.EmailAddress not in ('phaser@futurice.com', 'mailman@futurice.com', 'noreply@futurice.com', 'zabbix@futurice.com') group by timestamp;")
         ), ("resolved_other",
 		get_two_all("select DATE_FORMAT(Tickets.Resolved, '%j') as timestamp, count(*) as c from Tickets, Users where Tickets.Resolved >= date_sub(current_date, INTERVAL 120 day) and Tickets.Creator=Users.id and Users.EmailAddress not like '%@%futurice.com' group by timestamp;")
         ), ("resolved_machine",
 		get_two_all("select DATE_FORMAT(Tickets.Resolved, '%j') as timestamp, count(*) as c from Tickets, Users where Tickets.Resolved >= date_sub(current_date, INTERVAL 120 day) and Tickets.Creator=Users.id and (Users.EmailAddress like '%@%.futurice.com' or Users.EmailAddress in ('zabbix@futurice.com', 'mailman@futurice.com', 'noreply@futurice.com')) group by timestamp;")
        )]

        final_workflow = {"max": 0, "buckets": [], "authors": {
						"0": {"c": 0, "n": "Created by employees", "d": 0, "u": 0},
						"1": {"c": 0, "n": "Created by external", "d": 0, "u": 0},
						"2": {"c": 0, "n": "Created by machine", "d": 0, "u": 0},
						"3": {"c": 0, "n": "Employee ticket resolved", "d": 0, "u": 0},
						"4": {"c": 0, "n": "External ticket resolved", "d": 0, "u": 0},
						"5": {"c": 0, "n": "Machine ticket resolved", "d": 0, "u": 0}
			}}
        date_translations = {}
        current_date = int(datetime.date.today().strftime("%j"))
        date_translations[current_date] = 0
        count = 0
	counttemp = 0
        for numbers in range(current_date, 0, -1):
             counttemp += 1
             if counttemp % 7 == 0:
                 count = count - 1
             date_translations[numbers] = count
        for numbers in range(366, current_date, -1):
             counttemp += 1
             if counttemp % 7 == 0:
                 count = count - 1
             date_translations[numbers] = count

        list_temp = {}
        value_counters = [0,0,0,0,0,0]
        name_value_table = {"created_futu": 0, "created_other": 1, "created_machine": 2, "resolved_futu": 3, "resolved_other": 4, "resolved_machine": 5}
        for (name, items) in dictlist:
		for item in items:
			itemnum = date_translations[int(item)]
			if not list_temp.get(itemnum):
				list_temp[itemnum] = {}
			if not list_temp.get(itemnum).get(name):
				list_temp[itemnum][name] = 0
			list_temp[itemnum][name] += items.get(item)
			value_counters[name_value_table.get(name)] += items.get(item)
        for key in sorted(list_temp.iterkeys()):
             total = 0
             values_temp = list_temp.get(key)
             values = []
             for item in values_temp:
                 if values_temp.get(item) > final_workflow["max"]:
                     final_workflow["max"] = values_temp.get(item)
                 values.append([name_value_table[item], values_temp.get(item)])
                 total += values_temp.get(item)
             # sort values from highest to lowest
             values.sort(key=lambda x: x[1])
             final_workflow["buckets"].append({"d": int(time() + 7 * 86400 * (1 + key)), "i": values})

        c = 0
        for item in value_counters:
           final_workflow["authors"][str(c)]["c"] = item
           c += 1

        # distribution of subject occurance
        data["subject_occurance"] = get_two_all("select c as occurance, count(*) as count from (select count(*) as c from Tickets where Queue=1 group by Subject) as Subjects group by c;")

        data["workflow"] = final_workflow

        data["open_tickets"] = get_one("select count(*) as c from Tickets where (status='open' and (Queue=1 and Type!='reminder'));")
        data["new_tickets"] = get_one("select count(*) as c from Tickets where (status='new' and (Queue=1 and Type!='reminder'));")

        c = self.db.cursor()
        c.execute("select count(*) as c from Users where EmailAddress like '%.%@futurice.com';")
        (futurice_users, ) = c.fetchone()
        c.execute("select count(*) as c from Users where EmailAddress not like '%.%@futurice.com';")
        (other_users, ) = c.fetchone()
        data["other_users"] = other_users
        data["futurice_users"] = futurice_users
        c.close()
        self.send_data("tickets", data)


def main():
    a = RTStats()
    a.run()

if __name__ == '__main__':
    main()